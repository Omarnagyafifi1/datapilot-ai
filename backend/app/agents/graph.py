import json
import re
import sys
import tempfile
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
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

    trimmed = normalized[:5]
    if len(trimmed) < 3:
        return None

    return trimmed


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

    if len(normalized) != 3:
        return None

    return normalized


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
    return {"intent": "INQUIRE"}


def general_chat_node(state: AgentState, llm: BaseLLM) -> dict:
    prompt = f"The user said: {state.question}. Please respond politely as a helpful assistant."
    answer = llm.generate(prompt)
    return {"answer": answer, "success": True}


def schema_node(state: AgentState, schema_service: SchemaService) -> dict:
    schema = fetch_schema_context(schema_service, state.source_id)
    return {"documentation": {**state.documentation, "schema": schema}}


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

    # The user must provide a value like "approved" or "denied" to resume
    response = interrupt(
        {
            "question": state.question,
            "sql": state.sql,
            "message": "This operation modifies data. Do you approve the following SQL?",
        }
    )
    
    if response == "approved":
        return {"success": True} # Mark as ready for execution
    else:
        return {"success": False, "error": "User denied the operation", "answer": "Operation cancelled by user."}


def sql_execution_node(state: AgentState, db_service: DBService) -> dict:
    if _is_error_sql(state.sql):
        return {
            "query_results": [],
            "success": False,
            "error": state.sql.strip(),
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
    if not state.query_results:
        return {"visualization": None}

    try:
        import pandas as pd
        import plotly.express as px
    except Exception as exc:
        logger.warning("Visualization dependencies unavailable: %s", exc)
        return {"visualization": None}

    try:
        df = pd.DataFrame(state.query_results)
        if df.empty:
            return {"visualization": None}

        for column in df.columns:
            if df[column].dtype == "object":
                numeric_candidate = pd.to_numeric(df[column], errors="coerce")
                if numeric_candidate.notna().mean() >= 0.8:
                    df[column] = numeric_candidate
                    continue

                lower_column_name = str(column).lower()
                if any(token in lower_column_name for token in ("date", "time", "timestamp")):
                    datetime_candidate = pd.to_datetime(df[column], errors="coerce")
                    if datetime_candidate.notna().mean() >= 0.8:
                        df[column] = datetime_candidate

        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]

        fig = None
        chart_type = ""
        x_col = ""
        y_col = ""

        if datetime_cols and numeric_cols:
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            df_sorted = df.sort_values(by=x_col)
            fig = px.line(df_sorted, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
            chart_type = "line"
        elif categorical_cols and numeric_cols:
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
            grouped = (
                df.groupby(x_col, dropna=False)[y_col]
                .sum()
                .sort_values(ascending=False)
                .head(20)
                .reset_index()
            )
            fig = px.bar(grouped, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
            chart_type = "bar"
        elif len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
            chart_type = "scatter"
        elif len(numeric_cols) == 1:
            y_col = numeric_cols[0]
            fig = px.histogram(df, x=y_col, nbins=min(30, max(10, len(df) // 10)), title=f"Distribution of {y_col}")
            chart_type = "histogram"
        elif categorical_cols:
            x_col = categorical_cols[0]
            counts = (
                df[x_col]
                .astype(str)
                .fillna("N/A")
                .value_counts()
                .head(20)
                .rename_axis(x_col)
                .reset_index(name="count")
            )
            fig = px.bar(counts, x=x_col, y="count", title=f"Top values of {x_col}")
            chart_type = "bar"
            y_col = "count"

        if fig is None:
            return {"visualization": None}

        fig.update_layout(template="plotly_white")
        return {
            "visualization": {
                "library": "plotly",
                "chart_type": chart_type,
                "x": x_col,
                "y": y_col,
                "spec": json.loads(fig.to_json()),
            }
        }
    except Exception as exc:
        logger.warning("Visualization generation failed: %s", exc)
        return {"visualization": None}


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
    serialized_document = document.model_dump()
    logger.debug("%s", _json_dumps(serialized_document))
    return {"documentation": serialized_document, "executed_at": executed_at}


class AgentGraph:
    def __init__(
        self,
        llm: BaseLLM,
        db_service: DBService,
        schema_service: SchemaService,
    ) -> None:
        self.llm = llm
        self.db_service = db_service
        self.schema_service = schema_service
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("router", lambda s: intent_router_node(s, self.llm))
        workflow.add_node("general_chat", lambda s: general_chat_node(s, self.llm))
        workflow.add_node("fetch_schema", lambda s: schema_node(s, self.schema_service))
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

        # Edges
        workflow.add_edge(START, "router")
        
        def route_intent(state: AgentState) -> Literal["general_chat", "fetch_schema"]:
            return "general_chat" if state.intent == "GENERAL" else "fetch_schema"
            
        workflow.add_conditional_edges("router", route_intent, ["general_chat", "fetch_schema"])
        workflow.add_edge("general_chat", END)
        
        def route_sql_gen(state: AgentState) -> Literal["lookup_scenario", "generate_mod_sql"]:
            return "generate_mod_sql" if state.intent in ["ADD", "UPDATE", "DELETE"] else "lookup_scenario"
             
        workflow.add_conditional_edges("fetch_schema", route_sql_gen, ["lookup_scenario", "generate_mod_sql"])
        
        def route_scenario(state: AgentState) -> Literal["execute_sql", "generate_sql"]:
            return "execute_sql" if state.scenario_matched and bool(state.sql.strip()) else "generate_sql"

        workflow.add_conditional_edges("lookup_scenario", route_scenario, ["execute_sql", "generate_sql"])
        
        workflow.add_edge("generate_sql", "execute_sql")
        
        # Modification flow requires approval
        workflow.add_edge("generate_mod_sql", "approval")
        
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
        workflow.add_edge("document", END)

        return workflow.compile()

    def run(self, question: str, source_id: str, cli_mode: bool = False) -> dict[str, Any]:
        initial_state = {
            "question": question,
            "source_id": source_id,
            "documentation": {
                "dialect": self.db_service.get_dialect(source_id),
                "cli_mode": cli_mode,
            },
        }
        final_state = self.graph.invoke(initial_state)
        
        return {
            "sql": final_state.get("sql", ""),
            "results": final_state.get("query_results", []),
            # "visualization": final_state.get("visualization"),
            "documentation": final_state.get("documentation", {}),
        }

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
