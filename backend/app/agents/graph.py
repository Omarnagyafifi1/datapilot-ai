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

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, interrupt
from app.agents.nodes.sql_node import run_sql_node
from app.agents.prompts import (
    INSIGHT_PROMPT, 
    SUGGESTION_PROMPT, 
    INTENT_ROUTER_PROMPT, 
    VALIDATION_PROMPT,
    SQL_ADD_PROMPT,
    SQL_UPDATE_PROMPT,
    SQL_DELETE_PROMPT
)
from app.agents.state.agent_state import AgentState
from app.agents.tools.schema_tools import fetch_schema_context
from app.agents.tools.context_filtering import filter_schema_context
from app.agents.tools.sql_tool import execute_sql
from app.core.logger import get_logger
from app.llm.base_llm import BaseLLM
from app.models.schemas import QueryDocument
from app.agents.scenario_memory import ScenarioMemory
from app.services.db_service import DBService
from app.services.schema_service import SchemaService

logger = get_logger(__name__)
_ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")
_BIDI_CONTROL_PATTERN = re.compile(r"[\u200E\u200F\u202A-\u202E\u2066-\u2069]")
MAX_RETRIES = 3
SCENARIO_MEMORY = ScenarioMemory(Path(__file__).resolve().parents[2] / "scenarios.md")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _is_error_sql(sql: str) -> bool:
    return sql.strip().upper().startswith("ERROR:")


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


def _normalize_insights(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        payload = payload.get("insights")

    if not isinstance(payload, list):
        return None

    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        ar_value = item.get("ar")
        en_value = item.get("en")
        if not isinstance(ar_value, str) or not isinstance(en_value, str):
            continue

        ar_value = ar_value.strip()
        en_value = en_value.strip()
        if ar_value and en_value:
            normalized.append({"ar": ar_value, "en": en_value})

    if not normalized:
        return None

    return normalized[:5]


def _parse_insights(raw_response: str) -> list[dict[str, str]] | None:
    cleaned = _extract_json_payload(raw_response)
    candidates = [cleaned]

    list_start = cleaned.find("[")
    list_end = cleaned.rfind("]")
    if list_start != -1 and list_end > list_start:
        candidates.append(cleaned[list_start : list_end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        normalized = _normalize_insights(payload)
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
        if not isinstance(ar_value, str) or not isinstance(en_value, str):
            continue

        ar_value = ar_value.strip()
        en_value = en_value.strip()
        if ar_value and en_value:
            normalized.append({"ar": ar_value, "en": en_value})

    if not normalized:
        return None

    return normalized[:5]



def _parse_suggestions(raw_response: str) -> list[dict[str, str]] | None:
    cleaned = _extract_json_payload(raw_response)
    candidates = [cleaned]

    list_start = cleaned.find("[")
    list_end = cleaned.rfind("]")
    if list_start != -1 and list_end > list_start:
        candidates.append(cleaned[list_start : list_end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        normalized = _normalize_suggestions(payload)
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
    prompt = INTENT_ROUTER_PROMPT.format(question=state.question)
    intent = llm.generate(prompt).strip().upper()
    for valid_intent in ["GENERAL", "ADD", "DELETE", "UPDATE", "INQUIRE"]:
        if valid_intent in intent:
            return {"intent": valid_intent}

    normalized_question = state.question.strip().lower()
    if any(token in normalized_question for token in ["insert", "add", "create"]):
        return {"intent": "ADD"}
    if any(token in normalized_question for token in ["update", "set ", "edit", "change"]):
        return {"intent": "UPDATE"}
    if any(token in normalized_question for token in ["delete", "remove", "drop"]):
        return {"intent": "DELETE"}
    return {"intent": "INQUIRE"}


def general_chat_node(state: AgentState, llm: BaseLLM) -> dict:
    prompt = f"The user said: {state.question}. Please respond politely as a helpful assistant."
    answer = llm.generate(prompt)
    return {"answer": answer, "success": True}


def schema_node(state: AgentState, schema_service: SchemaService, llm: BaseLLM) -> dict:
    full_schema = fetch_schema_context(schema_service, state.source_id)
    filtered_schema = filter_schema_context(llm, full_schema, state.question)
    return {"documentation": {**state.documentation, "schema": filtered_schema}}


def scenario_lookup_node(state: AgentState) -> dict:
    matched = SCENARIO_MEMORY.find_similar_solution(state.question)
    if not matched:
        return {"scenario_matched": False, "scenario_similarity": 0.0}

    return {
        "sql": matched["sql"],
        "scenario_matched": True,
        "scenario_similarity": float(matched["score"]),
        "documentation": {
            **state.documentation,
            "scenario_reference_question": matched["question"],
        },
    }


def modification_sql_node(state: AgentState, llm: BaseLLM, schema_service: SchemaService) -> dict:
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
    
    sql = llm.generate(prompt)
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


def sql_execution_node(state: AgentState, db_service: DBService) -> dict:
    if _is_error_sql(state.sql):
        return {
            "query_results": [],
            "success": False,
            "error": state.sql.strip(),
            "retry_count": MAX_RETRIES,
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

    try:
        results = execute_sql(db_service, state.sql, state.source_id) or []
        return {"query_results": results, "success": True}
    except Exception as e:
        logger.error("SQL execution failed: %s", e)
        return {"query_results": [], "success": False, "error": str(e)}



def fix_sql_node(state: AgentState, llm: BaseLLM, schema_service: SchemaService, db_service: DBService) -> dict:
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
    
    prompt = SQL_FIX_PROMPT.format(
        dialect=db_service.get_dialect(),
        question=state.question,
        failed_query=state.sql,
        error_message=state.error or "Unknown error",
        schema=schema,
    )
    
    fixed_sql = llm.generate(prompt)
    
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


def validation_node(state: AgentState, llm: BaseLLM) -> dict:
    if not state.query_results:
        return {
            "validation_passed": False,
            "validation_reason": "No results returned",
            "retry_count": state.retry_count + 1,
        }
        
    prompt = VALIDATION_PROMPT.format(
        question=state.question,
        sql=state.sql,
        results=_json_dumps(state.query_results),
    )
    
    response = llm.generate(prompt).strip()
    if response.startswith("VALID"):
        return {"validation_passed": True, "validation_reason": None}
    else:
        return {
            "validation_passed": False,
            "validation_reason": response,
            "retry_count": state.retry_count + 1,
        }


def insight_node(state: AgentState, llm: BaseLLM) -> dict:
    if not state.query_results:
        return {"insights": _fallback_insights()}

    truncated_results = state.query_results[:50]
    prompt = (
        f"{INSIGHT_PROMPT}\n\n"
        f"Question:\n{state.question}\n\n"
        f"Query results (first {len(truncated_results)} rows):\n"
        f"{_json_dumps(truncated_results)}"
    )

    raw_response = llm.generate(prompt)
    parsed_insights = _parse_insights(raw_response)
    return {"insights": parsed_insights if parsed_insights is not None else _fallback_insights()}


def suggestion_node(state: AgentState, llm: BaseLLM) -> dict:
    if not state.query_results:
        return {"suggestions": []}

    prompt = (
        f"{SUGGESTION_PROMPT}\n\n"
        f"Question:\n{state.question}\n\n"
        f"Generated SQL:\n{state.sql}\n\n"
        f"Insights:\n{_json_dumps(state.insights)}"
    )

    raw_response = llm.generate(prompt)
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
    SCENARIO_MEMORY.append_entry(
        status="failed",
        question=state.question,
        sql=state.sql,
        error=state.error or state.validation_reason or "Unknown failure",
        validation_reason=state.validation_reason,
    )
    return {"success": False}


def visualization_node(state: AgentState) -> dict:
    result = generate_visualization(state.query_results, state.question)
    return {"visualization": result}


def documentation_node(state: AgentState) -> dict:
    executed_at = datetime.now(timezone.utc)
    document = QueryDocument(
        question=state.question,
        sql=state.sql,
        results=state.query_results,
        results_count=len(state.query_results),
        visualization=state.visualization,
        insights=state.insights,
        suggestions=state.suggestions,
        executed_at=executed_at.isoformat(),
    )
    serialized_document = {**state.documentation, **document.model_dump()}
    logger.debug("%s", _json_dumps(serialized_document))
    return {"documentation": serialized_document, "executed_at": executed_at}


def load_long_term_memory_node(
    state: AgentState,
    config: RunnableConfig,
    runtime: Runtime[Any],
) -> dict:
    store = runtime.store
    if store is None:
        return {}

    user_id = str(config.get("configurable", {}).get("user_id") or state.source_id)
    namespace = (user_id, "query_history")
    memories = list(store.search(namespace, query=state.question))

    memory_context: list[dict[str, Any]] = []
    for item in memories[:3]:
        value = getattr(item, "value", None)
        if isinstance(value, dict):
            memory_context.append(value)

    if not memory_context:
        return {}
    return {"documentation": {**state.documentation, "memory_context": memory_context}}


def persist_long_term_memory_node(
    state: AgentState,
    config: RunnableConfig,
    runtime: Runtime[Any],
) -> dict:
    store = runtime.store
    if store is None:
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
    store.put(namespace, memory_key, payload)
    return {}


class AgentGraph:
    def __init__(
        self,
        llm: BaseLLM,
        db_service: DBService,
        schema_service: SchemaService,
        checkpointer: Any | None = None,
        store: Any | None = None,
    ) -> None:
        self.llm = llm
        self.db_service = db_service
        self.schema_service = schema_service
        self.checkpointer = checkpointer
        self.store = store or InMemoryStore()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("router", lambda s: intent_router_node(s, self.llm))
        workflow.add_node("general_chat", lambda s: general_chat_node(s, self.llm))
        workflow.add_node("fetch_schema", lambda s: schema_node(s, self.schema_service, self.llm))
        workflow.add_node("load_memory", load_long_term_memory_node)
        workflow.add_node("lookup_scenario", scenario_lookup_node)
        workflow.add_node("generate_sql", lambda s: run_sql_node(s, self.llm))
        workflow.add_node("generate_mod_sql", lambda s: modification_sql_node(s, self.llm, self.schema_service))
        workflow.add_node("approval", approval_node)
        workflow.add_node("execute_sql", lambda s: sql_execution_node(s, self.db_service))
        workflow.add_node("fix_sql", lambda s: fix_sql_node(s, self.llm, self.schema_service, self.db_service))
        workflow.add_node("validate_result", lambda s: validation_node(s, self.llm))
        workflow.add_node("scenario_success", scenario_success_node)
        workflow.add_node("scenario_failure", scenario_failure_node)
        workflow.add_node("generate_visualization", visualization_node)
        workflow.add_node("generate_insights", lambda s: insight_node(s, self.llm))
        workflow.add_node("generate_suggestions", lambda s: suggestion_node(s, self.llm))
        workflow.add_node("document", documentation_node)
        workflow.add_node("persist_memory", persist_long_term_memory_node)

        # Edges
        workflow.add_edge(START, "router")
        
        def route_intent(state: AgentState) -> Literal["general_chat", "fetch_schema"]:
            return "general_chat" if state.intent == "GENERAL" else "fetch_schema"
            
        workflow.add_conditional_edges("router", route_intent, ["general_chat", "fetch_schema"])
        workflow.add_edge("general_chat", END)
        
        def route_sql_gen(state: AgentState) -> Literal["lookup_scenario", "generate_mod_sql", "execute_sql", "approval"]:
            if state.sql and state.sql.strip():
                if state.intent in ["ADD", "UPDATE", "DELETE"]:
                    return "approval"
                return "execute_sql"
            return "generate_mod_sql" if state.intent in ["ADD", "UPDATE", "DELETE"] else "lookup_scenario"
             
        workflow.add_edge("fetch_schema", "load_memory")
        workflow.add_conditional_edges("load_memory", route_sql_gen, ["lookup_scenario", "generate_mod_sql", "execute_sql", "approval"])
        
        def route_scenario(state: AgentState) -> Literal["execute_sql", "generate_sql", "persist_memory"]:
            if state.documentation.get("preview_only"):
                if state.scenario_matched and bool(state.sql.strip()):
                    return "persist_memory"
                return "generate_sql"
            return "execute_sql" if state.scenario_matched and bool(state.sql.strip()) else "generate_sql"

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
        
        def route_execution(state: AgentState) -> Literal["validate_result", "fix_sql", "scenario_failure"]:
            if state.success:
                return "validate_result"
            if state.retry_count >= MAX_RETRIES:
                return "scenario_failure"
            return "fix_sql"
              
        workflow.add_conditional_edges("execute_sql", route_execution, ["validate_result", "fix_sql", "scenario_failure"])

        def route_fix(state: AgentState) -> Literal["validate_result", "execute_sql", "scenario_failure"]:
            if state.success:
                return "validate_result"
            if state.retry_count >= MAX_RETRIES:
                return "scenario_failure"
            return "execute_sql"

        workflow.add_conditional_edges("fix_sql", route_fix, ["validate_result", "execute_sql", "scenario_failure"])

        def route_validation(state: AgentState) -> Literal["scenario_success", "generate_sql", "scenario_failure"]:
            if state.validation_passed:
                return "scenario_success"
            if state.retry_count >= MAX_RETRIES:
                return "scenario_failure"
            return "generate_sql"

        workflow.add_conditional_edges("validate_result", route_validation, ["scenario_success", "generate_sql", "scenario_failure"])
        workflow.add_edge("scenario_success", "generate_visualization")
        workflow.add_edge("generate_visualization", "generate_insights")
        workflow.add_edge("generate_insights", "generate_suggestions")
        workflow.add_edge("generate_suggestions", "document")
        workflow.add_edge("scenario_failure", "document")
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
        return self._format_output(final_state, resolved_thread_id)

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
    from app.services.schema_service import SchemaService
    
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
    schema_service = SchemaService()

    agent = AgentGraph(llm, db_service, schema_service)
    
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
