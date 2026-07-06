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


<<<<<<< HEAD
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
=======
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
>>>>>>> main
    return _graph_orchestrator


def reset_graph_orchestrator() -> None:
    """Reset the graph orchestrator so it rebuilds with updated settings on next request."""
    from app.llm.factory import _get_cached_llm
    global _graph_orchestrator
    _graph_orchestrator = None
    _get_cached_llm.cache_clear()
    logger.info("Graph orchestrator reset — will rebuild with new settings on next request")


def get_data_source_service() -> DataSourceService:
    return _data_source_service


def close_graph_orchestrator() -> None:
    _memory_backends.close()
    reset_graph_orchestrator()

def get_history_service() -> HistoryService:
    return _history_service
