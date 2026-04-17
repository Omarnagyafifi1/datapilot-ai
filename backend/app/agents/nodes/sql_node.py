from app.agents.prompts import SQL_GENERATION_PROMPT
from app.agents.state.agent_state import AgentState
from app.llm.base_llm import BaseLLM


def run_sql_node(state: AgentState, llm: BaseLLM) -> AgentState:
    prompt = f"{SQL_GENERATION_PROMPT}\nQuestion: {state.question}"
    state.sql = llm.generate(prompt)
    return state
