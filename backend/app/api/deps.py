import os

from app.agents.graph import AgentGraph
from app.agents.memory_backends import GraphMemoryBackends
from app.core.config import settings
from app.llm.factory import get_llm
from app.services.db_service import DBService
from app.services.data_source_service import DataSourceService
from app.services.schema_service import SchemaService
from app.services.history_service import HistoryService
from app.core.logger import get_logger

logger = get_logger(__name__)

_db_service = DBService()
_data_source_service = DataSourceService()
_schema_service = SchemaService()
_memory_backends = GraphMemoryBackends()
_graph_orchestrator: AgentGraph | None = None
_history_service = HistoryService()


def _init_langsmith() -> None:
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.LANGCHAIN_TRACING_V2 else "false"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
        logger.info(
            "LangSmith tracing enabled for project '%s'",
            settings.LANGCHAIN_PROJECT,
        )
    else:
        logger.info("LangSmith not configured (LANGCHAIN_API_KEY not set)")


_init_langsmith()


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

def get_history_service() -> HistoryService:
    return _history_service
