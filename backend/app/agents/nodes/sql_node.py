from app.agents.prompts import SQL_GENERATION_PROMPT, SQL_SYSTEM_MESSAGE
from app.agents.state.agent_state import AgentState
from app.llm.base_llm import BaseLLM


def _sanitize_sql(sql: str) -> str:
    """Strip markdown code fences that LLMs sometimes add."""
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            lines = lines[1:-1]
        elif len(lines) >= 2 and lines[0].strip().startswith("```"):
            lines = lines[1:]
        cleaned = "\n".join(lines).strip()
    return cleaned


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

    sql = _sanitize_sql(llm.generate(prompt, system_message=SQL_SYSTEM_MESSAGE, max_tokens=300))

    return {"sql": sql}
