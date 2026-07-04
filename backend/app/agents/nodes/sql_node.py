import re

from app.agents.prompts import SQL_GENERATION_PROMPT, SQL_SYSTEM_MESSAGE
from app.agents.state.agent_state import AgentState
from app.llm.base_llm import BaseLLM

_ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")


def _rewrite_arabic_columns(sql: str, schema: str) -> str:
    if not _ARABIC_PATTERN.search(sql) and not _ARABIC_PATTERN.search(schema) and "_ar" not in schema.lower():
        return sql

    _ar_columns: set[str] = set()
    for match in re.finditer(r"\b(\w+_ar)\b", schema.lower()):
        _ar_columns.add(match.group(1))

    if not _ar_columns:
        return sql

    rewritten = sql
    for ar_col in sorted(_ar_columns, key=len, reverse=True):
        base_name = ar_col[:-3]
        pattern = re.compile(rf"\b{re.escape(base_name)}\b", re.IGNORECASE)
        rewritten = pattern.sub(ar_col, rewritten)

    return rewritten


def run_sql_node(state: AgentState, llm: BaseLLM) -> dict:
    schema = state.documentation.get("schema", "No schema provided")
    max_rows = 1000
    scenario_context = state.documentation.get("scenario_context", "")

    prompt = SQL_GENERATION_PROMPT.format(
        schema=schema,
        max_rows=max_rows,
        question=state.question,
        scenario_context=scenario_context,
    )

    sql = llm.generate(prompt, system_message=SQL_SYSTEM_MESSAGE, max_tokens=300)

    if _ARABIC_PATTERN.search(state.question):
        rewritten = _rewrite_arabic_columns(sql, str(schema))
        if rewritten != sql:
            sql = rewritten

    return {"sql": sql}
