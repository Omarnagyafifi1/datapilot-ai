import re
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from app.agents.prompts import SQL_GENERATION_PROMPT, SQL_SYSTEM_MESSAGE, SQL_FIX_PROMPT
from app.agents.tools.schema_tools import fetch_schema_context
from app.services.db_service import DBService
from app.services.schema_service import SchemaService
from app.agents.state.agent_state import AgentState

MAX_RETRIES = 3
QUERY_TIMEOUT_SECONDS = 10
MAX_ROWS = 1000
RESULTS_FILE = Path("sql_results.txt")


def _sanitize_sql(sql: str) -> str:
    """Strip markdown code fences that LLMs sometimes add despite instructions."""
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            lines = lines[1:-1]
        elif len(lines) >= 2 and lines[0].strip().startswith("```"):
            lines = lines[1:]
        cleaned = "\n".join(lines).strip()
    return cleaned

_db_service: Optional[DBService] = None
_schema_service: Optional[SchemaService] = None
_redis_client = None
_llm = None


def init_sql_tool(
    db_service: DBService,
    schema_service: SchemaService,
    redis_client=None,
    llm=None,
) -> None:
    global _db_service, _schema_service, _redis_client, _llm
    
    _db_service = db_service
    _schema_service = schema_service
    _redis_client = redis_client
    _llm = llm


def execute_sql(db_service: DBService, sql: str, source_id: str) -> list[dict]:
    """Execute a SQL query using the provided DB service."""
    return db_service.run_query(sql, source_id=source_id)


def _write_results_file(results: list) -> None:
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        if not results:
            f.write("No results found.\n")
            return

        if isinstance(results, list) and results:
            headers = list(results[0].keys())
            f.write(" | ".join(headers) + "\n")
            f.write("-" * 40 + "\n")

            for row in results:
                f.write(" | ".join(str(v) for v in row.values()) + "\n")


def _validate_sql(sql: str) -> tuple[bool, str]:
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
    sql_upper = sql.upper()

    for keyword in forbidden:
        if re.search(rf"\b{keyword}\b", sql_upper):
            return False, f"Forbidden keyword '{keyword}' in query"

    return True, ""


@tool
def execute_sql_query(question: str) -> str:
    """Execute a SQL query to answer the user's question.

    Args:
        question: The user's question to answer via SQL query

    Returns:
        A message indicating success or failure with details
    """
    if not _db_service or not _schema_service or not _llm:
        return "Error: SQL tool not initialized. Call init_sql_tool first."

    state = AgentState(question=question, source_id="default")
    retry_count = 0
    success = False
    error = None
    sql_results = []

    schema_context = fetch_schema_context(_schema_service, state.source_id)
    if isinstance(schema_context, dict):
        schema_context = str(schema_context)

    while retry_count < MAX_RETRIES and not success:
        try:
            prompt = SQL_GENERATION_PROMPT.format(
                schema=schema_context,
                max_rows=MAX_ROWS,
                question=question,
                scenario_context="",
            )
            sql = _sanitize_sql(_llm.generate(prompt, system_message=SQL_SYSTEM_MESSAGE))

            if sql.startswith("ERROR:"):
                error = sql
                retry_count += 1
                continue

            valid, error = _validate_sql(sql)
            if not valid:
                retry_count += 1
                continue

            sql_results = _db_service.run_query(sql, timeout=QUERY_TIMEOUT_SECONDS)
            success = True

        except Exception as e:
            error = str(e)
            retry_count += 1

    _write_results_file(sql_results)

    if success:
        return f"Query executed successfully. Results written to {RESULTS_FILE}"
    else:
        return f"I couldn't write a valid query to answer this. Error: {error}"


@tool
def get_sql_results() -> str:
    """Read the SQL query results from the results file.

    Returns:
        The contents of sql_results.txt
    """
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No results file found. Execute a query first."


@tool
def fix_and_execute_sql(question: str, failed_query: str, error_message: str) -> str:
    """Fix a failed SQL query and re-execute it.

    Args:
        question: The original user question
        failed_query: The query that failed
        error_message: The error message from the failed execution

    Returns:
        Success or failure message
    """
    if not _db_service or not _schema_service or not _llm:
        return "Error: SQL tool not initialized. Call init_sql_tool first."

    schema_context = fetch_schema_context(_schema_service, "default")
    if isinstance(schema_context, dict):
        schema_context = str(schema_context)

    try:
        prompt = SQL_FIX_PROMPT.format(
            dialect=_db_service.get_dialect(),
            question=question,
            failed_query=failed_query,
            error_message=error_message,
            schema=schema_context,
            scenario_context="",
        )
        sql = _sanitize_sql(_llm.generate(prompt))

        valid, error = _validate_sql(sql)
        if not valid:
            return f"Query validation failed: {error}"

        sql_results = _db_service.run_query(sql, timeout=QUERY_TIMEOUT_SECONDS)
        _write_results_file(sql_results)

        return f"Query fixed and executed. Results written to {RESULTS_FILE}"

    except Exception as e:
        return f"Failed to fix query: {str(e)}"
