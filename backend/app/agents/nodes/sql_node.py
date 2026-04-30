from app.agents.prompts import SQL_GENERATION_PROMPT
from app.agents.state.agent_state import AgentState
from app.llm.base_llm import BaseLLM

def run_sql_node(state: AgentState, llm: BaseLLM) -> dict:
    # We fetch schema and max_rows if they exist in state/config, 
    # or rely on prompt defaults if not provided.
    # To be consistent with the current graph, we'll use a simplified prompt here 
    # or the node can be expanded to handle the format logic.
    
    schema = state.documentation.get("schema", "No schema provided")
    dialect = state.documentation.get("dialect", "sqlite")
    max_rows = 1000
    
    prompt = SQL_GENERATION_PROMPT.format(
        dialect=dialect,
        schema=schema,
        max_rows=max_rows,
        question=state.question
    )
    
    sql = llm.generate(prompt)
    return {"sql": sql}

