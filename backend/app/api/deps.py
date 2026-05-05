from redis import Redis

from app.agents.graph import AgentGraph
from app.core.config import settings
from app.llm.factory import get_llm
from app.services.approval_store import ApprovalStore
from app.services.db_service import DBService
from app.services.data_source_service import DataSourceService
from app.services.schema_service import SchemaService

_db_service = DBService()
_data_source_service = DataSourceService()
_schema_service = SchemaService()
_redis_client: Redis | None = None
_approval_store: ApprovalStore | None = None
_graph_orchestrator: AgentGraph | None = None


def get_graph_orchestrator() -> AgentGraph:
    global _graph_orchestrator

    if _graph_orchestrator is None:
        llm = get_llm(provider="mock")
        _graph_orchestrator = AgentGraph(llm=llm, db_service=_db_service, schema_service=_schema_service)

    return _graph_orchestrator


def get_data_source_service() -> DataSourceService:
    return _data_source_service


def get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    return _redis_client


def get_approval_store() -> ApprovalStore:
    global _approval_store

    if _approval_store is None:
        _approval_store = ApprovalStore(
            client=get_redis_client(),
            ttl_seconds=settings.APPROVAL_TTL_SECONDS,
        )

    return _approval_store
