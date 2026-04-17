from app.agents.graph import AgentGraph
from app.llm.factory import get_llm
from app.services.db_service import DBService
from app.services.schema_service import SchemaService


_db_service = DBService()
_schema_service = SchemaService()


def get_graph_orchestrator() -> AgentGraph:
    llm = get_llm(provider="mock")
    return AgentGraph(llm=llm, db_service=_db_service, schema_service=_schema_service)
