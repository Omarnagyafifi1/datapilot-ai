import json
import re
import sys
import tempfile
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4
from app.services.visualization_service import generate_visualization

try:
    from app.services.evaluation_service import evaluate_sql, post_evaluation_to_langsmith
    _EVAL_AVAILABLE = True
except Exception:
    _EVAL_AVAILABLE = False
    evaluate_sql = None
    post_evaluation_to_langsmith = None

from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, interrupt
from app.agents.nodes.sql_node import run_sql_node, _sanitize_sql
from app.agents.prompts import (
    INSIGHT_PROMPT,
    SUGGESTION_PROMPT,
    SQL_ADD_PROMPT,
    SQL_UPDATE_PROMPT,
    SQL_DELETE_PROMPT,
    SCENARIO_LESSON_PROMPT,
)
from app.agents.state.agent_state import AgentState
from app.agents.tools.schema_tools import fetch_schema_context
from app.agents.tools.context_filtering import filter_schema_context
from app.agents.tools.sql_tool import execute_sql
from app.core.logger import get_logger
from app.llm.base_llm import BaseLLM
from app.models.schemas import QueryDocument
from app.agents.scenario_memory import ScenarioMemory
from app.core.config import settings as app_settings
from app.services.db_service import DBService

logger = get_logger(__name__)
_ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")
_BIDI_CONTROL_PATTERN = re.compile(r"[\u200E\u200F\u202A-\u202E\u2066-\u2069]")
MAX_RETRIES = 3
SCENARIO_MEMORY = ScenarioMemory(Path(__file__).resolve().parents[2] / "scenarios.md")

# --- Semantic result cache ---
_SEMANTIC_CACHE: dict[str, dict] = {}
_SEMANTIC_CACHE_MAX = 100


def _question_hash(question: str) -> str:
    import hashlib
    tokens = re.findall(r"[a-zA-Z0-9_]+", question.lower())
    tokens.sort()
    return hashlib.md5(" ".join(tokens).encode()).hexdigest()[:16]


def _build_semantic_cache_key(source_id: str, question: str) -> str:
    return f"{source_id}::{_question_hash(question)}"


def _build_semantic_cache_storage_key(source_id: str, question: str, sql: str) -> str:
    prefix = sql.strip().lower()[:100]
    return f"{source_id}::{_question_hash(question)}::{hash(prefix)}"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _is_error_sql(sql: str) -> bool:
    upper = sql.strip().upper()
    return upper.startswith("ERROR:") or "SELECT 'ERROR:" in upper or 'SELECT "ERROR:' in upper


def _fallback_insights() -> list[dict[str, str]]:
    return [
        {
            "ar": "لا توجد بيانات كافية للتحليل", 
            "en": "No data to analyze"
        }
    ]


def _extract_json_payload(raw_response: str) -> str:
    cleaned = raw_response.strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return cleaned


def _safe_json_parse(text: str) -> Any | None:
    text = text.strip()

    m = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    for open_char, close_char in [('{', '}'), ('[', ']')]:
        start = text.find(open_char)
        end = text.rfind(close_char)
        if start != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                fixed = re.sub(r",\s*}", "}", candidate)
                fixed = re.sub(r",\s*\]", "]", fixed)
                fixed = re.sub(r"(?<!\\)'", '"', fixed)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return None


def _normalize_insights(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        if "ar" in payload or "en" in payload:
            payload = [payload]
        else:
            payload = payload.get("insights")

    if not isinstance(payload, list):
        return None

    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        ar_value = item.get("ar")
        en_value = item.get("en")

        if isinstance(ar_value, str) and ar_value.strip():
            ar_value = ar_value.strip()
        else:
            ar_value = ""

        if isinstance(en_value, str) and en_value.strip():
            en_value = en_value.strip()
        else:
            en_value = ""

        if not ar_value and not en_value:
            continue

        if not ar_value:
            ar_value = en_value
        if not en_value:
            en_value = ar_value

        normalized.append({"ar": ar_value, "en": en_value})

    if not normalized:
        return None

    return normalized[:5]


def _parse_insights(raw_response: str) -> list[dict[str, str]] | None:
    parsed = _safe_json_parse(raw_response)
    if parsed is None:
        return None

    normalized = _normalize_insights(parsed)
    if normalized is not None:
        return normalized

    return None


def _normalize_suggestions(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        payload = payload.get("suggestions")

    if not isinstance(payload, list):
        return None

    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        ar_value = item.get("ar")
        en_value = item.get("en")

        if isinstance(ar_value, str) and ar_value.strip():
            ar_value = ar_value.strip()
        else:
            ar_value = ""

        if isinstance(en_value, str) and en_value.strip():
            en_value = en_value.strip()
        else:
            en_value = ""

        if not ar_value and not en_value:
            continue

        if not ar_value:
            ar_value = en_value
        if not en_value:
            en_value = ar_value

        normalized.append({"ar": ar_value, "en": en_value})

    if not normalized:
        return None

    return normalized[:5]



def _parse_suggestions(raw_response: str) -> list[dict[str, str]] | None:
    parsed = _safe_json_parse(raw_response)
    if parsed is None:
        return None

    normalized = _normalize_suggestions(parsed)
    if normalized is not None:
        return normalized

    return None


def _format_rtl_for_cli(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: _format_rtl_for_cli(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_format_rtl_for_cli(item, key) for item in value]
    if isinstance(value, str) and key == "ar":
        # Remove embedded bidi control chars so they don't show as ‫...‬ in terminal output.
        sanitized = _BIDI_CONTROL_PATTERN.sub("", value)
        if _ARABIC_PATTERN.search(sanitized):
            return f"\u200F{sanitized}"
        return sanitized
    return value


def _open_visualization_in_browser(result: dict[str, Any]) -> bool:
    visualization = (result.get("documentation") or {}).get("visualization")
    if not isinstance(visualization, dict):
        return False

    spec = visualization.get("spec")
    if not isinstance(spec, dict):
        return False

    spec_json = json.dumps(spec, ensure_ascii=False, default=str)
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DataPilot Visualization</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0;padding:16px;font-family:Segoe UI,Arial,sans-serif;">
  <h3 style="margin:0 0 12px 0;">DataPilot Visualization</h3>
  <div id="chart" style="width:100%;height:80vh;"></div>
  <script>
    const fig = {spec_json};
    Plotly.newPlot('chart', fig.data || [], fig.layout || {{}}, fig.config || {{ responsive: true }});
  </script>
</body>
</html>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        html_path = f.name

    webbrowser.open(Path(html_path).as_uri())
    return True


def intent_router_node(state: AgentState, llm: BaseLLM) -> dict:
    import re
    from app.agents.prompts import INTENT_ROUTER_PROMPT

    normalized_question = state.question.strip().lower()

    # ── 1. Read / inquiry signals (check BEFORE write keywords) ──
    # Questions starting with interrogative words or common read verbs
    # are almost always INQUIRE, even if they contain words like "new",
    # "change", "set", etc.
    _READ_STARTERS = (
        r'^(how|what|which|where|when|who|why|does|do|is|are|was|were|'
        r'can|could|will|would|shall|should|has|have|had|did)\b'
    )
    _READ_VERBS = (
        r'\b(show|list|display|find|get|fetch|count|total|average|sum|'
        r'calculate|compare|report|describe|explain|tell|give|select|'
        r'search|look\s*up|retrieve|check|aggregate|log|logs|'
        r'analyze|analysis|analyse|trend|trends|group|breakdown)\b'
    )
    # Arabic interrogatives
    _AR_READ = (
        r'(ما\s|من\s|كم\s|أين|متى|لماذا|هل\s|كيف|ما هي|ما هو|من هم|'
        r'اعرض|أظهر|عرض|اذكر)'
    )

    is_read_question = bool(
        re.search(_READ_STARTERS, normalized_question)
        or re.search(_READ_VERBS, normalized_question)
        or re.search(_AR_READ, state.question.strip())
    )

    if is_read_question:
        return {"intent": "INQUIRE"}

    # ── 3. Write-intent heuristics (strict patterns only) ──
    # Only match when the verb clearly signals a write *command*,
    # not when it appears incidentally inside a read question.
    _ADD_PATTERNS = (
        r'(?:^|\b)(?:insert|add|create|append)\s+'       # imperative: "add a row", "insert into"
        r'|'
        r'(?:^|\b)(?:i\s+want\s+to|please)\s+(?:insert|add|create)'
    )
    _UPDATE_PATTERNS = (
        r'(?:^|\b)(?:update|modify|edit|change|rename|replace|set)\s+'
        r'|'
        r'(?:^|\b)(?:i\s+want\s+to|please)\s+(?:update|modify|edit|change|rename)'
    )
    _DELETE_PATTERNS = (
        r'(?:^|\b)(?:delete|remove|destroy|purge|erase)\s+'
        r'|'
        r'(?:^|\b)(?:i\s+want\s+to|please)\s+(?:delete|remove|drop)'
    )

    if re.search(_ADD_PATTERNS, normalized_question):
        return {"intent": "ADD"}
    if re.search(_UPDATE_PATTERNS, normalized_question):
        return {"intent": "UPDATE"}
    if re.search(_DELETE_PATTERNS, normalized_question):
        return {"intent": "DELETE"}

    # ── 3. Ambiguous — fall back to LLM classification ──
    prompt = INTENT_ROUTER_PROMPT.format(question=state.question)
    raw_intent = llm.generate(prompt, max_tokens=20).strip().upper()

    # Accept only known categories; default to INQUIRE for safety
    if raw_intent in {"ADD", "DELETE", "UPDATE", "INQUIRE"}:
        return {"intent": raw_intent}
    return {"intent": "INQUIRE"}


def schema_node(state: AgentState, schema_service: Any, llm: BaseLLM) -> dict:
    full_schema = fetch_schema_context(schema_service, state.source_id)
    filtered_schema = filter_schema_context(llm, full_schema, state.question)
    return {"documentation": {**state.documentation, "schema": filtered_schema}}


def combined_router_and_filter_node(state: AgentState, llm: BaseLLM, schema_service: Any) -> dict:
    """Merge intent routing and schema filtering into one LLM call when both are needed."""
    import json
    import re
    from app.agents.prompts import ROUTER_AND_FILTER_PROMPT

    # 1. Determine intent via heuristics first (fast path, no LLM)
    normalized_question = state.question.strip().lower()
    _READ_STARTERS = (
        r'^(how|what|which|where|when|who|why|does|do|is|are|was|were|'
        r'can|could|will|would|shall|should|has|have|had|did)\b'
    )
    _READ_VERBS = (
        r'\b(show|list|display|find|get|fetch|count|total|average|sum|'
        r'calculate|compare|report|describe|explain|tell|give|select|'
        r'search|look\s*up|retrieve|check|aggregate|log|logs|'
        r'analyze|analysis|analyse|trend|trends|group|breakdown)\b'
    )
    _AR_READ = (
        r'(ما\s|من\s|كم\s|أين|متى|لماذا|هل\s|كيف|ما هي|ما هو|من هم|'
        r'اعرض|أظهر|عرض|اذكر)'
    )
    is_read_question = bool(
        re.search(_READ_STARTERS, normalized_question)
        or re.search(_READ_VERBS, normalized_question)
        or re.search(_AR_READ, state.question.strip())
    )
    if is_read_question:
        heuristic_intent = "INQUIRE"
    else:
        _ADD_PATTERNS = r'(?:^|\b)(?:insert|add|create|append)\s+|(?:^|\b)(?:i\s+want\s+to|please)\s+(?:insert|add|create)'
        _UPDATE_PATTERNS = r'(?:^|\b)(?:update|modify|edit|change|rename|replace|set)\s+|(?:^|\b)(?:i\s+want\s+to|please)\s+(?:update|modify|edit|change|rename)'
        _DELETE_PATTERNS = r'(?:^|\b)(?:delete|remove|destroy|purge|erase)\s+|(?:^|\b)(?:i\s+want\s+to|please)\s+(?:delete|remove|drop)'
        if re.search(_ADD_PATTERNS, normalized_question):
            heuristic_intent = "ADD"
        elif re.search(_UPDATE_PATTERNS, normalized_question):
            heuristic_intent = "UPDATE"
        elif re.search(_DELETE_PATTERNS, normalized_question):
            heuristic_intent = "DELETE"
        else:
            heuristic_intent = None  # ambiguous — need LLM

    # 2. Get full schema
    full_schema = fetch_schema_context(schema_service, state.source_id)

    # 3. Decide: do we need an LLM call?
    schema_data = json.loads(full_schema)
    tables = schema_data.get("tables", [])
    needs_filter = len(tables) > 20
    needs_intent_llm = heuristic_intent is None

    if needs_intent_llm or needs_filter:
        if needs_intent_llm and needs_filter:
            # One combined call for both intent + filter
            prompt = ROUTER_AND_FILTER_PROMPT.format(
                full_schema=full_schema,
                question=state.question,
            )
            raw = llm.generate(prompt, max_tokens=1024).strip()
            import re as _re2
            m = _re2.search(r'\{.*\}', raw, _re2.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                    intent = parsed.get("intent", heuristic_intent or "INQUIRE")
                    filtered = parsed.get("filtered_schema", schema_data)
                    if isinstance(intent, str) and intent.upper() in {"ADD", "DELETE", "UPDATE", "INQUIRE"}:
                        pass
                    else:
                        intent = heuristic_intent or "INQUIRE"
                    if not filtered.get("tables"):
                        filtered = schema_data
                    return {
                        "intent": intent.upper(),
                        "documentation": {**state.documentation, "schema": json.dumps(filtered)},
                    }
                except Exception:
                    pass
            # Fall through to individual handling
            return {
                "intent": heuristic_intent or "INQUIRE",
                "documentation": {**state.documentation, "schema": full_schema},
            }
        elif needs_intent_llm:
            from app.agents.prompts import INTENT_ROUTER_PROMPT
            prompt = INTENT_ROUTER_PROMPT.format(question=state.question)
            raw_intent = llm.generate(prompt, max_tokens=20).strip().upper()
            intent = raw_intent if raw_intent in {"ADD", "DELETE", "UPDATE", "INQUIRE"} else "INQUIRE"
            return {
                "intent": intent,
                "documentation": {**state.documentation, "schema": full_schema},
            }
        else:
            # Only need filtering
            from app.agents.tools.context_filtering import filter_schema_context
            filtered = filter_schema_context(llm, full_schema, state.question)
            return {
                "intent": heuristic_intent,
                "documentation": {**state.documentation, "schema": filtered},
            }

    # 4. No LLM call needed — heuristic intent + unfiltered schema
    return {
        "intent": heuristic_intent,
        "documentation": {**state.documentation, "schema": full_schema},
    }


def _get_valid_table_names(schema_str: str) -> set[str]:
    try:
        schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
        return {t["name"].lower() for t in schema.get("tables", []) if "name" in t}
    except Exception:
        return set()


def _filter_scenario_context_to_schema(context: str, schema_str: str) -> str:
    valid_tables = _get_valid_table_names(schema_str)
    if not valid_tables:
        return context

    lines = context.splitlines()
    filtered: list[str] = []
    current_block: list[str] = []
    in_sql = False

    for line in lines:
        if line.startswith("Example "):
            if current_block:
                block_text = "\n".join(current_block)
                sql_match = re.search(r"SQL:\s*(.*)", block_text)
                if sql_match:
                    sql = sql_match.group(1)
                    refs = re.findall(r'(?:(?:"?\w+"?)\.)?(?:"?\w+"?)', sql)
                    # Extract potential table names (words that might be tables)
                    tokens = re.findall(r'\b[a-z_][a-z0-9_]*\b', sql.lower())
                    referenced_tables = {t for t in tokens if t in valid_tables}
                    if referenced_tables:
                        filtered.extend(current_block)
                    # If no tables from current schema found in SQL, skip this block
                else:
                    filtered.extend(current_block)
                current_block = []
            current_block.append(line)
        else:
            current_block.append(line)

    if current_block:
        block_text = "\n".join(current_block)
        sql_match = re.search(r"SQL:\s*(.*)", block_text)
        if sql_match:
            sql = sql_match.group(1)
            tokens = re.findall(r'\b[a-z_][a-z0-9_]*\b', sql.lower())
            referenced_tables = {t for t in tokens if t in valid_tables}
            if referenced_tables:
                filtered.extend(current_block)
        else:
            filtered.extend(current_block)

    return "\n".join(filtered)


def scenario_lookup_node(state: AgentState) -> dict:
    matched = SCENARIO_MEMORY.find_similar_solution(state.question)
    scenario_context = SCENARIO_MEMORY.get_recent_context(n=10)

    schema_str = state.documentation.get("schema", "")
    if schema_str:
        scenario_context = _filter_scenario_context_to_schema(scenario_context, schema_str)

    result: dict = {
        "scenario_matched": False,
        "scenario_similarity": 0.0,
        "documentation": {
            **state.documentation,
            "scenario_context": f"\n### Past Query Examples (Learn from these)\n{scenario_context}\n",
        },
    }

    if matched:
        matched_schema_valid = True
        if schema_str:
            valid_tables = _get_valid_table_names(schema_str)
            matched_sql = matched.get("sql", "")
            tokens = re.findall(r'\b[a-z_][a-z0-9_]*\b', matched_sql.lower())
            matched_tables = {t for t in tokens if t in valid_tables}
            if not matched_tables:
                matched_schema_valid = False

        if matched_schema_valid:
            result["scenario_matched"] = True
            result["scenario_similarity"] = float(matched["score"])
            result["documentation"]["scenario_reference_question"] = matched["question"]
            result["documentation"]["scenario_reference_sql"] = matched["sql"]
            matched_note = (
                f"\n### Matched Reference (similarity={float(matched['score']):.2f})\n"
                f"  Question: {matched['question']}\n"
                f"  SQL: {matched['sql']}\n"
            )
            result["documentation"]["scenario_context"] = (
                result["documentation"]["scenario_context"] + matched_note
            )

    return result


def _is_mock_output(output: str) -> bool:
    upper = output.strip().upper()
    if upper.startswith("MOCK") or "MOCK RESPONSE" in upper:
        return True
    if "INSERT statement" in output or "UPDATE statement" in output or "DELETE statement" in output:
        return True
    return False


def modification_sql_node(state: AgentState, llm: BaseLLM, schema_service: Any) -> dict:
    schema = fetch_schema_context(schema_service, state.source_id)
    dialect = state.documentation.get("dialect", "sqlite")
    prompt_map = {
        "ADD": SQL_ADD_PROMPT,
        "UPDATE": SQL_UPDATE_PROMPT,
        "DELETE": SQL_DELETE_PROMPT
    }
    prompt_tmpl = prompt_map.get(state.intent, SQL_ADD_PROMPT)
    
    prompt = prompt_tmpl.format(
        dialect=dialect,
        schema=schema,
        question=state.question
    )
    
    sql = _sanitize_sql(llm.generate(prompt, max_tokens=300))
    
    if _is_mock_output(sql):
        logger.warning(
            "LLM returned mock/nonsense output for modification query '%s' — resetting to empty",
            state.question[:80],
        )
        sql = ""

    return {"sql": sql}


def approval_node(state: AgentState) -> dict:
    # Human-in-the-loop interrupt
    if state.documentation.get("cli_mode"):
        print("\nApproval required for write operation.")
        print("SQL to execute:")
        print(state.sql)
        response = input("Approve execution? [y/N]: ").strip().lower()
        approved = response in {"y", "yes", "approved"}
        if approved:
            return {"success": True}
        return {"success": False, "error": "User denied the operation", "answer": "Operation cancelled by user."}

    # For API flows, interrupt and wait for a resume value.
    response = interrupt(
        {
            "question": state.question,
            "sql": state.sql,
            "message": "This operation modifies data. Do you approve the following SQL?",
            "intent": state.intent,
        }
    )

    approved = False
    if isinstance(response, bool):
        approved = response
    elif isinstance(response, str):
        approved = response.strip().lower() in {"approved", "approve", "yes", "y", "true", "1"}
    elif isinstance(response, dict):
        approved = bool(response.get("approved"))

    if approved:
        return {"success": True}
    return {"success": False, "error": "User denied the operation", "answer": "Operation cancelled by user."}


_FORBIDDEN_SQL_KEYWORDS_ALWAYS = {"DROP", "ALTER", "TRUNCATE", "GRANT", "REVOKE", "EXEC"}
_FORBIDDEN_SQL_KEYWORDS_READONLY = {"INSERT", "UPDATE", "DELETE"} | _FORBIDDEN_SQL_KEYWORDS_ALWAYS


def _validate_sql_keywords(sql: str, intent: str) -> str | None:
    """Return an error message if the SQL contains forbidden keywords, else None."""
    import re

    forbidden = (
        _FORBIDDEN_SQL_KEYWORDS_ALWAYS
        if intent in {"ADD", "UPDATE", "DELETE"}
        else _FORBIDDEN_SQL_KEYWORDS_READONLY
    )
    sql_upper = sql.upper()
    for keyword in forbidden:
        if re.search(rf"\b{keyword}\b", sql_upper):
            return f"Blocked: forbidden keyword '{keyword}' in generated SQL"
    return None


_STALE_CACHE: dict[str, list[dict]] = {}
_STALE_CACHE_MAX = 50


def _cache_key(sql: str, source_id: str) -> str:
    return f"{source_id}:::{sql.strip().lower()}"


def sql_execution_node(state: AgentState, db_service: DBService) -> dict:
    current_retry = state.retry_count
    is_write = state.intent in {"ADD", "UPDATE", "DELETE"}

    if _is_error_sql(state.sql):
        return {
            "query_results": [],
            "success": False,
            "error": state.sql.strip(),
            "retry_count": MAX_RETRIES,
        }

    if not state.sql or not state.sql.strip():
        return {
            "query_results": [],
            "success": False,
            "error": "Empty SQL query. Could not generate a valid query from the question.",
            "retry_count": current_retry + 1,
        }

    # Programmatic SQL safety check — blocks dangerous keywords
    validation_error = _validate_sql_keywords(state.sql, state.intent)
    if validation_error:
        logger.warning("SQL blocked by keyword validation: %s", validation_error)
        return {
            "query_results": [],
            "success": False,
            "error": validation_error,
            "retry_count": MAX_RETRIES,
        }

    # Check cache (skip for write operations — they must always execute)
    ck = _cache_key(state.sql, state.source_id)
    if not is_write and ck in _STALE_CACHE:
        logger.debug("SQL cache hit for: %s", state.sql[:60])
        return {"query_results": list(_STALE_CACHE[ck]), "success": True}

    try:
        results = execute_sql(db_service, state.sql, state.source_id) or []
        # Only cache read queries
        if not is_write:
            if len(_STALE_CACHE) >= _STALE_CACHE_MAX:
                _STALE_CACHE.pop(next(iter(_STALE_CACHE)))
            _STALE_CACHE[ck] = list(results)
        else:
            # Invalidate both caches after writes — data has changed
            from app.services.db_service import _SCHEMA_CACHE
            _SCHEMA_CACHE.pop(state.source_id, None)
            keys_to_remove = [k for k in _STALE_CACHE if k.startswith(f"{state.source_id}:::")]
            for k in keys_to_remove:
                _STALE_CACHE.pop(k, None)
        return {"query_results": results, "success": True}
    except Exception as e:
        logger.error("SQL execution failed: %s", e)
        return {
            "query_results": [],
            "success": False,
            "error": str(e),
            "retry_count": current_retry + 1,
        }



def fix_sql_node(state: AgentState, llm: BaseLLM, schema_service: Any, db_service: DBService) -> dict:
    if state.success:
        return {}

    if _is_error_sql(state.sql):
        return {
            "query_results": [],
            "success": False,
            "error": state.sql.strip(),
            "retry_count": MAX_RETRIES,
        }

    current_retry = state.retry_count + 1
    schema = fetch_schema_context(schema_service, state.source_id)
    from app.agents.prompts import SQL_FIX_PROMPT
    
    scenario_context = state.documentation.get("scenario_context", "")
    
    prompt = SQL_FIX_PROMPT.format(
        dialect=db_service.get_dialect(state.source_id),
        question=state.question,
        failed_query=state.sql,
        error_message=state.error or "Unknown error",
        schema=schema,
        scenario_context=scenario_context,
    )
    
    fixed_sql = _sanitize_sql(llm.generate(prompt, max_tokens=300))

    import re as _re
    if fixed_sql.strip().rstrip(";").strip().upper() in ("SELECT 1", "SELECT 1;"):
        logger.warning("fix_sql_node generated noop '%s' for '%s'", fixed_sql, state.question[:80])
        return {
            "sql": fixed_sql,
            "query_results": [],
            "success": False,
            "error": "Could not generate a valid query for this question. The database schema does not contain the requested data or table.",
            "retry_count": MAX_RETRIES,
        }

    try:
        results = execute_sql(db_service, fixed_sql, state.source_id) or []
        return {
            "sql": fixed_sql,
            "query_results": results,
            "success": True,
            "error": None,
            "retry_count": current_retry,
            "documentation": {**state.documentation, "schema": schema},
        }
    except Exception as e:
        error_text = str(e)
        refreshed_schema = schema
        if any(token in error_text.lower() for token in ["no such table", "relation", "does not exist"]):
            refreshed_schema = fetch_schema_context(schema_service, state.source_id)
        return {
            "sql": fixed_sql,
            "error": error_text,
            "success": False,
            "retry_count": current_retry,
            "documentation": {**state.documentation, "schema": refreshed_schema},
        }





def _truncate_cell_values(rows: list[dict], max_len: int = 100) -> list[dict]:
    truncated: list[dict] = []
    for row in rows:
        t = {}
        for k, v in row.items():
            if isinstance(v, str) and len(v) > max_len:
                t[k] = v[:max_len] + "..."
            else:
                t[k] = v
        truncated.append(t)
    return truncated


def _build_insight_prompt(state: AgentState) -> str:
    truncated_results = state.query_results[:10]
    if truncated_results and len(truncated_results[0]) > 5:
        keys = list(truncated_results[0].keys())[:5]
        truncated_results = [{k: row.get(k) for k in keys} for row in truncated_results]
    truncated_results = _truncate_cell_values(truncated_results)

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return (
        f"{INSIGHT_PROMPT}\n\n"
        f"Current Date: {current_date}\n\n"
        f"Question:\n{state.question}\n\n"
        f"Query results (first {len(truncated_results)} rows):\n"
        f"{_json_dumps(truncated_results)}"
    )


def insight_node(state: AgentState, llm: BaseLLM) -> dict:
    if not state.query_results:
        logger.info("insight_node: query_results empty (%s rows), returning fallback", len(state.query_results))
        return {"insights": _fallback_insights()}

    prompt = _build_insight_prompt(state)

    raw_response = llm.generate(prompt, max_tokens=512)
    logger.info("insight_node raw_response=%s", raw_response[:500])
    parsed_insights = _parse_insights(raw_response)
    if parsed_insights is not None:
        logger.info("insight_node: returning insights count=%d", len(parsed_insights))
        return {"insights": parsed_insights}

    logger.info("insight_node: parse failed for raw_response=%s", raw_response[:300])
    return {"insights": _fallback_insights()}


def suggestion_node(state: AgentState, llm: BaseLLM) -> dict:
    if not state.query_results:
        return {"suggestions": []}

    results_preview = []
    if state.query_results:
        preview = state.query_results[:1]
        if preview:
            keys = list(preview[0].keys())[:5]
            results_preview = [{k: row.get(k) for k in keys} for row in preview]

    prompt = (
        f"{SUGGESTION_PROMPT}\n\n"
        f"Question:\n{state.question}\n\n"
        f"Generated SQL:\n{state.sql}\n\n"
        f"Sample Results (first {len(results_preview)} row):\n{_json_dumps(results_preview)}"
    )

    raw_response = llm.generate(prompt, max_tokens=192)
    parsed_suggestions = _parse_suggestions(raw_response)
    return {"suggestions": parsed_suggestions if parsed_suggestions is not None else []}


def scenario_success_node(state: AgentState) -> dict:
    if state.success and state.sql and not _is_error_sql(state.sql):
        SCENARIO_MEMORY.append_entry(
            status="resolved",
            question=state.question,
            sql=state.sql,
            validation_reason=state.validation_reason,
        )
    return {}


def scenario_failure_node(state: AgentState) -> dict:
    # Store the failure details in the documentation so the lesson node can use them
    return {
        "success": False,
        "documentation": {
            **state.documentation,
            "_failure_question": state.question,
            "_failure_sql": state.sql,
            "_failure_error": state.error or state.validation_reason or "Unknown failure",
            "_failure_validation": state.validation_reason,
        },
    }


def scenario_lesson_node(state: AgentState, llm: BaseLLM, schema_service: Any) -> dict:
    failure_question = state.documentation.get("_failure_question") or state.question
    failure_sql = state.documentation.get("_failure_sql") or state.sql
    failure_error = state.documentation.get("_failure_error") or "Unknown failure"
    schema = fetch_schema_context(schema_service, state.source_id)

    prompt = SCENARIO_LESSON_PROMPT.format(
        question=failure_question,
        failed_sql=failure_sql,
        error_message=failure_error,
        schema=schema,
    )

    try:
        lesson_text = llm.generate(prompt, max_tokens=800)
    except Exception:
        lesson_text = None

    SCENARIO_MEMORY.append_entry(
        status="failed",
        question=failure_question,
        sql=failure_sql,
        error=failure_error,
        validation_reason=state.documentation.get("_failure_validation"),
        lesson=lesson_text,
    )

    if lesson_text:
        logger.info("Lesson documented for failed query: %s", failure_question[:80])

    return {}


def visualization_node(state: AgentState) -> dict:
    result = generate_visualization(state.query_results, state.question)
    return {"visualization": result}


def _coerce_visualization(raw: Any) -> Any:
    from app.models.schemas import VisualizationResponse
    if raw is None:
        return None
    if isinstance(raw, VisualizationResponse):
        return raw
    if isinstance(raw, dict):
        try:
            return VisualizationResponse(**raw)
        except Exception:
            return None
    return None


def documentation_node(state: AgentState) -> dict:
    executed_at = datetime.now(timezone.utc)
    document = QueryDocument(
        question=state.question,
        sql=state.sql,
        results=state.query_results,
        results_count=len(state.query_results),
        visualization=_coerce_visualization(state.visualization),
        insights=state.insights,
        suggestions=state.suggestions,
        executed_at=executed_at.isoformat(),
    )
    serialized_document = {**state.documentation, **document.model_dump()}
    logger.debug("%s", _json_dumps(serialized_document))
    return {"documentation": serialized_document, "executed_at": executed_at}


def _make_load_long_term_memory_node(store: Any):
    def load_long_term_memory_node(
        state: AgentState,
        config: RunnableConfig,
    ) -> dict:
        local_store = store
        if local_store is None:
            return {}

        user_id = str(config.get("configurable", {}).get("user_id") or state.source_id)
        namespace = (user_id, "query_history")
        memories = list(local_store.search(namespace, query=state.question))

        memory_context: list[dict[str, Any]] = []
        for item in memories[:3]:
            value = getattr(item, "value", None)
            if isinstance(value, dict):
                memory_context.append(value)

        if not memory_context:
            return {}
        return {"documentation": {**state.documentation, "memory_context": memory_context}}
    return load_long_term_memory_node


def _make_persist_long_term_memory_node(store: Any):
    def persist_long_term_memory_node(
        state: AgentState,
        config: RunnableConfig,
    ) -> dict:
        local_store = store
        if local_store is None:
            return {}

        user_id = str(config.get("configurable", {}).get("user_id") or state.source_id)
        namespace = (user_id, "query_history")
        memory_key = str(uuid4())
        payload = {
            "question": state.question,
            "intent": state.intent,
            "sql": state.sql,
            "success": state.success,
            "results_count": len(state.query_results),
            "error": state.error,
            "executed_at": (state.executed_at.isoformat() if state.executed_at else None),
        }
        local_store.put(namespace, memory_key, payload)
        return {}
    return persist_long_term_memory_node


class AgentGraph:
    def __init__(
        self,
        llm: BaseLLM,
        db_service: DBService,
        schema_service: Any,
        checkpointer: Any | None = None,
        store: Any | None = None,
    ) -> None:
        self.llm = llm
        self.db_service = db_service
        self.schema_service = schema_service
        self.checkpointer = checkpointer
        self.store = store or InMemoryStore()
        self.graph = self._build_graph()

    def _post_process_node(self, state: AgentState) -> dict:
        """Run visualization, insights, and suggestions in parallel via ThreadPoolExecutor."""
        results: dict[str, Any] = {}

        def run_vis(s: AgentState) -> dict:
            return visualization_node(s)

        def run_insights(s: AgentState) -> dict:
            return insight_node(s, self.llm)

        def run_suggestions(s: AgentState) -> dict:
            return suggestion_node(s, self.llm)

        tasks = {
            "visualization": run_vis,
            "insights": run_insights,
            "suggestions": run_suggestions,
        }

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(fn, state): key for key, fn in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    result = future.result()
                    results.update(result)
                except Exception:
                    logger.exception("post_process_node %s failed", key)
                    if key == "insights":
                        results["insights"] = _fallback_insights()
                    elif key == "suggestions":
                        results["suggestions"] = []
                    elif key == "visualization":
                        results["visualization"] = None

        return results

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("router_and_filter", lambda s: combined_router_and_filter_node(s, self.llm, self.schema_service))
        workflow.add_node("load_memory", _make_load_long_term_memory_node(self.store))
        workflow.add_node("lookup_scenario", scenario_lookup_node)
        workflow.add_node("generate_sql", lambda s: run_sql_node(s, self.llm))
        workflow.add_node("generate_mod_sql", lambda s: modification_sql_node(s, self.llm, self.schema_service))
        workflow.add_node("approval", approval_node)
        workflow.add_node("execute_sql", lambda s: sql_execution_node(s, self.db_service))
        workflow.add_node("fix_sql", lambda s: fix_sql_node(s, self.llm, self.schema_service, self.db_service))

        workflow.add_node("scenario_success", scenario_success_node)
        workflow.add_node("scenario_failure", scenario_failure_node)
        workflow.add_node("scenario_lesson", lambda s: scenario_lesson_node(s, self.llm, self.schema_service))
        workflow.add_node("post_process", self._post_process_node)
        workflow.add_node("document", documentation_node)
        workflow.add_node("persist_memory", _make_persist_long_term_memory_node(self.store))

        # Edges
        workflow.add_edge(START, "router_and_filter")
        
        def route_sql_gen(state: AgentState) -> Literal["lookup_scenario", "generate_mod_sql", "execute_sql", "approval"]:
            if state.sql and state.sql.strip():
                if state.intent in ["ADD", "UPDATE", "DELETE"]:
                    return "approval"
                return "execute_sql"
            return "generate_mod_sql" if state.intent in ["ADD", "UPDATE", "DELETE"] else "lookup_scenario"
             
        workflow.add_edge("router_and_filter", "load_memory")
        workflow.add_conditional_edges("load_memory", route_sql_gen, ["lookup_scenario", "generate_mod_sql", "execute_sql", "approval"])
        
        def route_scenario(state: AgentState) -> Literal["execute_sql", "generate_sql", "persist_memory"]:
            if state.sql and state.sql.strip():
                return "execute_sql"
            return "generate_sql"

        workflow.add_conditional_edges("lookup_scenario", route_scenario, ["execute_sql", "generate_sql", "persist_memory"])
        
        def route_after_sql_gen(state: AgentState) -> Literal["execute_sql", "persist_memory"]:
            if state.documentation.get("preview_only"):
                return "persist_memory"
            return "execute_sql"
            
        workflow.add_conditional_edges("generate_sql", route_after_sql_gen, ["execute_sql", "persist_memory"])
        
        # Modification flow requires approval unless preview_only
        def route_after_mod_sql_gen(state: AgentState) -> Literal["approval", "persist_memory"]:
            if state.documentation.get("preview_only"):
                return "persist_memory"
            return "approval"
            
        workflow.add_conditional_edges("generate_mod_sql", route_after_mod_sql_gen, ["approval", "persist_memory"])
        
        def route_approval(state: AgentState) -> Literal["execute_sql", "__end__"]:
            return "execute_sql" if state.success else "__end__"
            
        workflow.add_conditional_edges("approval", route_approval, ["execute_sql", "__end__"])
        
        def route_execution(state: AgentState) -> Literal["scenario_success", "fix_sql", "scenario_failure"]:
            if state.success:
                return "scenario_success"
            if state.retry_count >= MAX_RETRIES:
                return "scenario_failure"
            return "fix_sql"
              
        workflow.add_conditional_edges("execute_sql", route_execution, ["scenario_success", "fix_sql", "scenario_failure"])

        def route_fix(state: AgentState) -> Literal["scenario_success", "execute_sql", "scenario_failure"]:
            if state.success:
                return "scenario_success"
            if state.retry_count >= MAX_RETRIES:
                return "scenario_failure"
            return "execute_sql"

        workflow.add_conditional_edges("fix_sql", route_fix, ["scenario_success", "execute_sql", "scenario_failure"])
        workflow.add_edge("scenario_success", "post_process")
        workflow.add_edge("post_process", "document")
        workflow.add_edge("scenario_failure", "scenario_lesson")
        workflow.add_edge("scenario_lesson", "document")
        workflow.add_edge("document", "persist_memory")
        workflow.add_edge("persist_memory", END)

        return workflow.compile(checkpointer=self.checkpointer, store=self.store)

    @staticmethod
    def _extract_interrupt_payload(final_state: dict[str, Any]) -> dict[str, Any] | None:
        interrupts = final_state.get("__interrupt__")
        if not interrupts:
            return None
        first_interrupt = interrupts[0]
        payload = getattr(first_interrupt, "value", first_interrupt)
        if isinstance(payload, dict):
            return payload
        return {"value": payload}

    @staticmethod
    def _format_output(final_state: dict[str, Any], thread_id: str) -> dict[str, Any]:
        interrupt_payload = AgentGraph._extract_interrupt_payload(final_state)
        return {
            "sql": final_state.get("sql", ""),
            "results": final_state.get("query_results", []),
            "visualization": final_state.get("visualization"),
            "insights": final_state.get("insights", []),
            "suggestions": final_state.get("suggestions", []),
            "documentation": final_state.get("documentation", {}),
            "thread_id": thread_id,
            "requires_approval": interrupt_payload is not None,
            "approval_request": interrupt_payload,
            "status": "awaiting_approval" if interrupt_payload is not None else "completed",
        }

    def run(
        self,
        question: str,
        source_id: str,
        cli_mode: bool = False,
        thread_id: str | None = None,
        preview_only: bool = False,
        sql: str | None = None,
    ) -> dict[str, Any]:
        # Check semantic cache before any LLM calls
        cache_key = _build_semantic_cache_key(source_id, question)
        cached = _SEMANTIC_CACHE.get(cache_key)
        if cached and not preview_only and not sql:
            logger.info("Semantic cache HIT for question: %s", question[:60])
            return dict(cached)  # return a copy

        resolved_thread_id = thread_id or str(uuid4())
        initial_state = {
            "question": question,
            "source_id": source_id,
            "sql": sql or "",
            "documentation": {
                "dialect": self.db_service.get_dialect(source_id),
                "cli_mode": cli_mode,
                "preview_only": preview_only,
            },
        }
        config = {"configurable": {"thread_id": resolved_thread_id}}
        config["configurable"]["user_id"] = source_id
        final_state = self.graph.invoke(initial_state, config=config)
        output = self._format_output(final_state, resolved_thread_id)

        # Store in semantic cache on success
        if not preview_only and output.get("status") == "completed" and not output.get("requires_approval"):
            store_key = _build_semantic_cache_storage_key(
                source_id, question, output.get("sql", "")
            )
            if len(_SEMANTIC_CACHE) >= _SEMANTIC_CACHE_MAX:
                _SEMANTIC_CACHE.pop(next(iter(_SEMANTIC_CACHE)))
            _SEMANTIC_CACHE[cache_key] = dict(output)
            _SEMANTIC_CACHE[store_key] = dict(output)

        if _EVAL_AVAILABLE and not preview_only:
            import random
            if random.random() < app_settings.EVALUATION_SAMPLE_RATE:
                try:
                    generated_sql = final_state.get("sql", output.get("sql", ""))
                    results = final_state.get("query_results", output.get("results", []))
                    dialect = (final_state.get("documentation") or {}).get("dialect", "sqlite")
                    
                    def _run_eval():
                        try:
                            eval_scores = evaluate_sql(
                                question=question,
                                sql=generated_sql,
                                results=results,
                                dialect=dialect,
                                llm=self.llm,
                            )
                            post_evaluation_to_langsmith(
                                question=question,
                                sql=generated_sql,
                                source_id=source_id,
                                thread_id=resolved_thread_id,
                                scores=eval_scores,
                                latency=0.0,
                                results_count=len(results),
                                has_visualization=output.get("visualization") is not None,
                                insight_count=len(output.get("insights", [])),
                            )
                        except Exception as exc:
                            logger.warning("Background evaluation failed: %s", exc)

                    import threading
                    threading.Thread(target=_run_eval, daemon=True).start()
                except Exception as exc:
                    logger.warning("Failed to start background evaluation: %s", exc)

        return output

    def resume(self, thread_id: str, approved: bool) -> dict[str, Any]:
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = self.graph.get_state(config)
        values = getattr(state_snapshot, "values", {}) or {}
        source_id = values.get("source_id")
        if source_id:
            config["configurable"]["user_id"] = str(source_id)
        final_state = self.graph.invoke(Command(resume=approved), config=config)
        return self._format_output(final_state, thread_id)

if __name__ == "__main__":
    # This part allows you to run the agent from the CLI for testing
    import os
    from app.core.config import settings
    from app.llm.factory import get_llm
    from app.services.db_service import DBService, get_engine, upload_csv_to_sqlite

    
    source_choice = input("Choose data source type [1=CSV, 2=Database]: ").strip()
    if source_choice not in {"1", "2"}:
        print("Error: Please choose 1 for CSV or 2 for Database.")
        exit(1)
    
    source_id = "cli_test"
    if source_choice == "1":
        csv_path = input("Please enter the path to your CSV file: ").strip().strip('"')
        if not os.path.exists(csv_path):
            print(f"Error: File not found at {csv_path}")
            exit(1)

        print(f"Uploading {csv_path} to temporary database...")
        try:
            _, table_name = upload_csv_to_sqlite(csv_path, source_id)
            print(f"Uploaded to table: {table_name}")
        except Exception as e:
            print(f"Error uploading CSV: {e}")
            exit(1)
    else:
        source_id = "cli_db"
        conn_string = settings.DATABASE_URL.strip()
        if not conn_string:
            print("Error: DATABASE_URL is empty in .env/config.")
            exit(1)

        db_service = DBService(source_id=source_id, conn_string=conn_string)
        try:
            get_engine(source_id=source_id, conn_string=conn_string)
            print("Database connection configured successfully from .env DATABASE_URL.")
        except Exception as e:
            print(f"Error configuring database connection: {e}")
            exit(1)

    # Setup Groq LLM
    llm = get_llm(provider="openrouter") 
    db_service = DBService(source_id=source_id)
    agent = AgentGraph(llm, db_service, None)
    
    test_question = input("Enter your question: ").strip()
    
    print(f"Querying: {test_question}")
    result = agent.run(test_question, source_id, cli_mode=True)
    opened = _open_visualization_in_browser(result)

    result_for_cli = dict(result)
    documentation = dict(result.get("documentation") or {})
    visualization = documentation.get("visualization")
    if isinstance(visualization, dict):
        documentation["visualization"] = {
            "library": visualization.get("library"),
            "chart_type": visualization.get("chart_type"),
            "x": visualization.get("x"),
            "y": visualization.get("y"),
            "opened_in_browser": opened,
        }
    result_for_cli["documentation"] = documentation

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(_format_rtl_for_cli(result_for_cli), indent=2, ensure_ascii=False, default=str))
