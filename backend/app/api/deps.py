from app.agents.graph import AgentGraph
from app.agents.memory_backends import GraphMemoryBackends
from app.core.config import settings
from app.llm.factory import get_llm
from app.services.db_service import DBService
from app.services.data_source_service import DataSourceService
from app.services.schema_service import SchemaService
from app.services.history_service import HistoryService

# LLM settings service - fallback to empty settings if not available
try:
    from app.services.llm_settings_service import get_llm_settings
except ImportError:
    def get_llm_settings():
        return {}

_db_service = DBService()
_data_source_service = DataSourceService()
_schema_service = SchemaService()
_memory_backends = GraphMemoryBackends()
_graph_orchestrator: AgentGraph | None = None
_history_service = HistoryService()


def get_graph_orchestrator(
    provider: str = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    api_keys: dict = None,
) -> AgentGraph:
    """
    Get the graph orchestrator with optional LLM config override.
    
    If config params are provided, creates a fresh orchestrator with those settings.
    Otherwise returns the cached orchestrator with saved/default settings.
    """
    # If config override is provided, create a new orchestrator
    if any(x is not None for x in [provider, model, temperature, max_tokens, api_keys]):
        runtime_settings = get_llm_settings()
        
        if provider is None:
            provider = runtime_settings.get("provider", settings.DEFAULT_LLM_PROVIDER)
        if model is None:
            model = runtime_settings.get("model", settings.DEFAULT_LLM_MODEL)
        if temperature is None:
            temperature = runtime_settings.get("temperature", 0.2)
        if max_tokens is None:
            max_tokens = runtime_settings.get("max_tokens", 2048)
        if api_keys is None:
            api_keys = runtime_settings.get("api_keys", {})
        
        llm = get_llm(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_keys=api_keys,
        )
        return AgentGraph(
            llm=llm,
            db_service=_db_service,
            schema_service=_schema_service,
            checkpointer=_memory_backends.checkpointer,
            store=_memory_backends.store,
        )
    
    # Return cached orchestrator
    global _graph_orchestrator
    if _graph_orchestrator is None:
        runtime_settings = get_llm_settings()
        llm = get_llm(
            provider=runtime_settings.get("provider"),
            model=runtime_settings.get("model"),
            temperature=runtime_settings.get("temperature"),
            max_tokens=runtime_settings.get("max_tokens"),
            api_keys=runtime_settings.get("api_keys"),
        )
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
