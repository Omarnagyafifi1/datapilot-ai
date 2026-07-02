from app.core.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.providers.groq_llm import GroqLLM
from app.llm.providers.openrouter_llm import OpenRouterLLM
from app.llm.providers.gemini_llm import GeminiLLM
from app.llm.providers.lite_llm import LiteLLMProvider
from app.services.settings_service import _load
from app.core.logger import get_logger

from functools import lru_cache

logger = get_logger(__name__)

VALID_PROVIDERS = {"groq", "openrouter", "gemini", "litellm"}

@lru_cache(maxsize=4)
def _get_cached_llm(provider: str, groq_key: str, openrouter_key: str, gemini_key: str) -> BaseLLM:
    if provider == "groq":
        return GroqLLM(api_key=groq_key)
    elif provider == "openrouter":
        return OpenRouterLLM(api_key=openrouter_key)
    elif provider == "gemini":
        return GeminiLLM(api_key=gemini_key)
    elif provider == "litellm":
        return LiteLLMProvider(api_keys={"groq": groq_key, "openrouter": openrouter_key, "gemini": gemini_key})
    raise ValueError(f"Unknown LLM provider '{provider}'. Valid: {', '.join(sorted(VALID_PROVIDERS))}")


def _sanitize_key(key: str | None) -> str:
    if not key:
        return ""
    # Strip any hidden non-ASCII characters (like zero-width spaces or directional markers)
    return key.encode("ascii", "ignore").decode("ascii").strip()

def get_llm(provider: str | None = None) -> BaseLLM:
    """Factory method to get an LLM instance based on dynamic settings or .env"""
    dynamic_settings = _load()
    api_keys = dynamic_settings.get("api_keys", {})

    groq_key = _sanitize_key(api_keys.get("groq") or settings.GROQ_API_KEY)
    openrouter_key = _sanitize_key(api_keys.get("openrouter") or settings.OPENROUTER_API_KEY)
    gemini_key = _sanitize_key(api_keys.get("gemini") or settings.GEMINI_API_KEY)

    provider = provider or dynamic_settings.get("llm_provider") or settings.LLM_PROVIDER
    if provider:
        provider = provider.strip().lower()
    if provider not in VALID_PROVIDERS:
        provider = "litellm"
        
    return _get_cached_llm(provider, groq_key, openrouter_key, gemini_key)
