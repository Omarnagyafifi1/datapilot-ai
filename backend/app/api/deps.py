import os

from app.core.config import settings
from app.core.logger import get_logger
from app.agents.graph import AgentGraph
from app.agents.memory_backends import GraphMemoryBackends
from app.llm.factory import get_llm
from app.services.db_service import DBService
from app.services.data_source_service import DataSourceService
from app.services.schema_service import SchemaService
from app.services.history_service import HistoryService

logger = get_logger(__name__)


_db_service = DBService()
_data_source_service = DataSourceService()
_schema_service = SchemaService()
_memory_backends = GraphMemoryBackends()
_graph_orchestrator: AgentGraph | None = None
_history_service = HistoryService()


def get_graph_orchestrator() -> AgentGraph:
    global _graph_orchestrator
    if _graph_orchestrator is None:
        try:
            # Use dynamic settings (settings.json) as the source of truth.
            # Falls back to .env LLM_PROVIDER only if no dynamic setting is saved.
            llm = get_llm()
            _graph_orchestrator = AgentGraph(
                llm=llm,
                db_service=_db_service,
                schema_service=_schema_service,
                checkpointer=_memory_backends.checkpointer,
                store=_memory_backends.store,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
    return _graph_orchestrator


def reset_graph_orchestrator() -> None:
    """Reset the graph orchestrator so it rebuilds with updated settings on next request."""
    global _graph_orchestrator
    _graph_orchestrator = None
    logger.info("Graph orchestrator reset — will rebuild with new settings on next request")


def get_data_source_service() -> DataSourceService:
    return _data_source_service


def close_graph_orchestrator() -> None:
    _memory_backends.close()
    reset_graph_orchestrator()

def get_history_service() -> HistoryService:
    return _history_service