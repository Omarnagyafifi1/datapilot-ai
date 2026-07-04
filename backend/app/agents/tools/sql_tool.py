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
    return db_service.run_query(sql, source_id=source_id, timeout=QUERY_TIMEOUT_SECONDS)


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


# Unused LangChain tool wrappers removed for code quality and dead code cleanup.
