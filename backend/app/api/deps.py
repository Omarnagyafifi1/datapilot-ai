from app.agents.graph import AgentGraph
from app.llm.factory import get_llm
from app.services.db_service import DBService
from app.services.data_source_service import DataSourceService
from app.services.schema_service import SchemaService
from app.services.history_service import HistoryService

_db_service = DBService()
_data_source_service = DataSourceService()
_schema_service = SchemaService()
_history_service = HistoryService()


def get_graph_orchestrator() -> AgentGraph:
    llm = get_llm(provider="mock")
    return AgentGraph(llm=llm, db_service=_db_service, schema_service=_schema_service)


def get_data_source_service() -> DataSourceService:
    return _data_source_service


def get_history_service() -> HistoryService:
    return _history_service
