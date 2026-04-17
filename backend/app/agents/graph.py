from app.agents.base_agent import BaseAgent
from app.agents.nodes.sql_node import run_sql_node
from app.agents.state.agent_state import AgentState
from app.agents.tools.schema_tools import fetch_schema_context
from app.agents.tools.sql_tools import execute_sql
from app.llm.base_llm import BaseLLM
from app.services.db_service import DBService
from app.services.schema_service import SchemaService


class AgentGraph(BaseAgent):
    def __init__(
        self,
        llm: BaseLLM,
        db_service: DBService,
        schema_service: SchemaService,
    ) -> None:
        self.llm = llm
        self.db_service = db_service
        self.schema_service = schema_service

    def run(self, question: str) -> str:
        state = AgentState(question=question)

        # Simple orchestration flow: schema -> SQL generation -> SQL execution -> answer.
        _schema = fetch_schema_context(self.schema_service)
        state = run_sql_node(state, self.llm)
        result = execute_sql(self.db_service, state.sql)

        state.answer = f"Stub answer. Schema: {_schema}. Result: {result}"
        return state.answer
