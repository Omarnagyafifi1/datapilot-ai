from app.agents.prompts import SQL_GENERATION_PROMPT, SQL_SYSTEM_MESSAGE
from app.agents.state.agent_state import AgentState
from app.llm.base_llm import BaseLLM

def run_sql_node(state: AgentState, llm: BaseLLM) -> dict:
    schema = state.documentation.get("schema", "No schema provided")
    max_rows = 1000
    
    prompt = SQL_GENERATION_PROMPT.format(
        schema=schema,
        max_rows=max_rows,
        question=state.question
    )
    
    sql = llm.generate(prompt, system_message=SQL_SYSTEM_MESSAGE)
    return {"sql": sql}

