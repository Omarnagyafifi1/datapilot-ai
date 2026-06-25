from app.agents.graph import AgentGraph
from app.agents.memory_backends import GraphMemoryBackends
from app.core.config import settings
from app.llm.factory import get_llm
from app.services.db_service import DBService
from app.services.data_source_service import DataSourceService
from app.services.schema_service import SchemaService

_db_service = DBService()
_data_source_service = DataSourceService()
_schema_service = SchemaService()
_memory_backends = GraphMemoryBackends()
_graph_orchestrator: AgentGraph | None = None


def get_graph_orchestrator() -> AgentGraph:
    global _graph_orchestrator
    if _graph_orchestrator is None:
        llm = get_llm(provider=settings.LLM_PROVIDER)
        _graph_orchestrator = AgentGraph(
            llm=llm,
            db_service=_db_service,
            schema_service=_schema_service,
            checkpointer=_memory_backends.checkpointer,
            store=_memory_backends.store,
        )
    return _graph_orchestrator


def get_data_source_service() -> DataSourceService:
    return _data_source_service


def close_graph_orchestrator() -> None:
    _memory_backends.close()
