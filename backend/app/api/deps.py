from redis import Redis

from app.agents.graph import AgentGraph
from app.agents.memory_backends import GraphMemoryBackends
from app.core.config import settings
from app.llm.factory import get_llm
from app.services.approval_store import ApprovalStore
from app.services.db_service import DBService
from app.services.data_source_service import DataSourceService
from app.services.schema_service import SchemaService
from app.services.history_service import HistoryService

_db_service = DBService()
_data_source_service = DataSourceService()
_schema_service = SchemaService()
_memory_backends = GraphMemoryBackends()
_history_service = HistoryService()
_redis_client: Redis | None = None
_approval_store: ApprovalStore | None = None
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

def get_history_service() -> HistoryService:
    return _history_service

def get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

    return _redis_client


def get_approval_store() -> ApprovalStore:
    global _approval_store

    if _approval_store is None:
        _approval_store = ApprovalStore(
            client=get_redis_client(),
            ttl_seconds=settings.approval_ttl_seconds,
        )

    return _approval_store
