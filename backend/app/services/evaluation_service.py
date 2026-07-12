from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.llm.base_llm import BaseLLM

logger = get_logger(__name__)

try:
    from langsmith import Client as LangSmithClient

    _LANGSMITH_AVAILABLE = bool(settings.LANGCHAIN_API_KEY)
    if _LANGSMITH_AVAILABLE:
        _LS_CLIENT = LangSmithClient(
            api_key=settings.LANGCHAIN_API_KEY,
            api_url=settings.LANGCHAIN_ENDPOINT,
        )
    else:
        _LS_CLIENT = None
except Exception:
    _LANGSMITH_AVAILABLE = False
    _LS_CLIENT = None


SQL_SYNTAX_CHECK_PROMPT = """You are a SQL syntax validator. Check if the following SQL is syntactically valid for {dialect}.

SQL:
{sql}

Respond with ONLY a JSON object:
{{"valid": true/false, "error": "error message if invalid, else null", "dialect": "{dialect}"}}
"""

SQL_CORRECTNESS_PROMPT = """You are a Text-to-SQL quality evaluator. Given a user question, the generated SQL, and the query results, evaluate:

1. **Correctness**: Does the SQL correctly answer the question? (0.0 - 1.0)
2. **Completeness**: Does the SQL cover all aspects of the question? (0.0 - 1.0)
3. **Efficiency**: Is the SQL reasonably efficient for the task? (0.0 - 1.0)

Question: {question}
Generated SQL:
{sql}

Results (first 5 rows):
{results}

Respond with ONLY a JSON object:
{{"correctness": 0.0-1.0, "completeness": 0.0-1.0, "efficiency": 0.0-1.0, "explanation": "brief reasoning"}}
"""

SCHEMA_RELEVANCE_PROMPT = """You are a schema relevance evaluator. Given a user question and the SQL query, determine if the SQL uses the correct tables and columns.

Question: {question}
Generated SQL:
{sql}

Respond with ONLY a JSON object:
{{"tables_correct": true/false, "columns_correct": true/false, "score": 0.0-1.0, "issues": "any mismatches found or null if none"}}
"""


def _syntax_check(sql: str, dialect: str = "sqlite") -> dict[str, Any]:
    if not sql or not sql.strip():
        return {"valid": False, "error": "Empty SQL", "dialect": dialect}

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
    for keyword in forbidden:
        if re.search(rf"\b{keyword}\b", sql.upper()):
            return {"valid": False, "error": f"Forbidden keyword '{keyword}' in query", "dialect": dialect}

    basic_pattern = re.compile(
        r"^\s*(SELECT|WITH|EXPLAIN)\b",
        re.IGNORECASE,
    )
    if not basic_pattern.match(sql):
        return {"valid": False, "error": "SQL must start with SELECT, WITH, or EXPLAIN", "dialect": dialect}

    has_from = re.search(r"\bFROM\b", sql, re.IGNORECASE)
    if not has_from:
        return {"valid": False, "error": "SQL must contain a FROM clause", "dialect": dialect}

    has_select_col = re.search(r"SELECT\s+.+", sql, re.IGNORECASE | re.DOTALL)
    if not has_select_col:
        return {"valid": False, "error": "SQL must select at least one column", "dialect": dialect}

    if sql.count("(") != sql.count(")"):
        return {"valid": False, "error": "Unbalanced parentheses", "dialect": dialect}

    return {"valid": True, "error": None, "dialect": dialect}


def _llm_eval(prompt: str, llm: BaseLLM | None) -> dict[str, Any] | None:
    if not llm:
        return None
    try:
        response = llm.generate(prompt)
        cleaned = response.strip()

        result = _safe_parse_json(cleaned)
        if result is not None:
            return result

        logger.warning("LLM evaluation returned non-JSON: %.200s", cleaned)
        return None
    except Exception as e:
        logger.warning("LLM evaluation failed: %s", e)
        return None


def _safe_parse_json(text: str) -> dict | None:
    text = text.strip()

    # Strategy 1: Extract from markdown code block
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        result = _try_json_loads(m.group(1))
        if result is not None:
            return result

    # Strategy 2: Find first { and last }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        result = _try_json_loads(candidate)
        if result is not None:
            return result
        # with single-quote fix
        result = _try_json_loads(_fix_single_quotes(candidate))
        if result is not None:
            return result

    # Strategy 3: ast.literal_eval handles Python dicts natively
    try:
        import ast
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return None


def _try_json_loads(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _fix_single_quotes(text: str) -> str:
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*\]", "]", text)
    text = re.sub(r"(?<!\\)'", '"', text)
    return text


def evaluate_sql(
    question: str,
    sql: str,
    results: list[dict[str, Any]] | None,
    dialect: str = "sqlite",
    llm: BaseLLM | None = None,
    source_id: str = "",
    thread_id: str = "",
) -> dict[str, Any]:
    scores = {
        "syntax_valid": False,
        "syntax_error": None,
        "correctness": 0.0,
        "completeness": 0.0,
        "efficiency": 0.0,
        "schema_score": 0.0,
        "overall": 0.0,
    }

    syntax_result = _syntax_check(sql, dialect)
    scores["syntax_valid"] = syntax_result["valid"]
    scores["syntax_error"] = syntax_result["error"]

    if syntax_result["valid"]:
        scores["schema_score"] = 1.0
        scores["correctness"] = 0.5
        scores["completeness"] = 0.5
        scores["efficiency"] = 0.5

    if llm and syntax_result["valid"]:
        results_preview = results[:5] if results else []
        correctness_prompt = SQL_CORRECTNESS_PROMPT.format(
            question=question,
            sql=sql,
            results=results_preview,
        )
        schema_prompt = SCHEMA_RELEVANCE_PROMPT.format(question=question, sql=sql)
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_correctness = executor.submit(_llm_eval, correctness_prompt, llm)
            future_schema = executor.submit(_llm_eval, schema_prompt, llm)
            
            eval_result = future_correctness.result()
            schema_result = future_schema.result()

        if eval_result:
            scores["correctness"] = float(eval_result.get("correctness", 0.0))
            scores["completeness"] = float(eval_result.get("completeness", 0.0))
            scores["efficiency"] = float(eval_result.get("efficiency", 0.0))

        if schema_result:
            scores["schema_score"] = float(schema_result.get("score", 0.0))

    scores["overall"] = round(
        (
            scores["correctness"] * 0.4
            + scores["completeness"] * 0.25
            + scores["efficiency"] * 0.15
            + scores["schema_score"] * 0.1
            + (1.0 if scores["syntax_valid"] else 0.0) * 0.1
        ),
        2,
    )

    return scores


def _is_valid_uuid(value: str) -> bool:
    try:
        import uuid
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _resolve_run_id(thread_id: str) -> str:
    """Find the LangSmith run_id associated with a thread by listing recent runs."""
    try:
        runs = list(_LS_CLIENT.list_runs(
            run_type="chain",
            filter={"tags": [f"thread_id:{thread_id}"]},
            limit=1,
        ))
        if runs:
            return str(runs[0].id)
    except Exception:
        logger.debug("Could not resolve run_id for thread %s", thread_id, exc_info=True)
    return thread_id


def post_evaluation_to_langsmith(
    question: str,
    sql: str,
    source_id: str,
    thread_id: str,
    scores: dict[str, Any],
    latency: float,
    results_count: int,
    has_visualization: bool,
    insight_count: int,
) -> bool:
    if not _LANGSMITH_AVAILABLE or not _LS_CLIENT:
        logger.debug("LangSmith not configured, skipping evaluation posting")
        return False

    if not _is_valid_uuid(thread_id):
        logger.debug("thread_id is not a valid UUID, skipping LangSmith feedback: %s", thread_id)
        return False

    resolved_run_id = _resolve_run_id(thread_id)

    try:
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="sql_syntax_valid",
            score=1.0 if scores.get("syntax_valid") else 0.0,
            comment=scores.get("syntax_error"),
        )
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="overall_quality",
            score=scores.get("overall", 0.0),
        )
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="correctness",
            score=scores.get("correctness", 0.0),
        )
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="completeness",
            score=scores.get("completeness", 0.0),
        )
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="latency",
            score=min(latency / 30.0, 1.0),
        )
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="has_visualization",
            score=1.0 if has_visualization else 0.0,
        )
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="results_count",
            score=min(results_count / 1000.0, 1.0),
        )
        _LS_CLIENT.create_feedback(
            run_id=resolved_run_id,
            key="insight_count",
            score=min(insight_count / 5.0, 1.0),
        )

        logger.info(
            "LangSmith evaluation posted for thread=%s overall=%.2f",
            thread_id,
            scores.get("overall", 0.0),
        )
        return True
    except Exception as e:
        logger.warning("Failed to post evaluation to LangSmith: %s", e)
        return False
