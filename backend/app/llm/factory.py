from functools import lru_cache
from typing import Optional

from app.core.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.providers.groq_llm import GroqLLM
from app.llm.providers.openrouter_llm import OpenRouterLLM
from app.llm.providers.gemini_llm import GeminiLLM
from app.llm.providers.lite_llm import LiteLLMProvider
from app.llm.providers.azure_openai_llm import AzureOpenAILLM
from app.services.settings_service import _load
from app.core.logger import get_logger

logger = get_logger(__name__)

VALID_PROVIDERS = {"groq", "openrouter", "gemini", "litellm", "azure", "mock"}


class FallbackLLM(BaseLLM):
    def __init__(self, primary_provider: str, providers_map: dict) -> None:
        self.primary_provider = primary_provider
        self.providers_map = providers_map

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        # Determine fallback order starting with the primary provider
        order = [self.primary_provider]
        for p in ["azure", "groq", "gemini", "openrouter"]:
            if p not in order and p in self.providers_map:
                order.append(p)

        last_exc = None
        for provider_name in order:
            llm = self.providers_map[provider_name]
            try:
                logger.debug(f"Attempting generation with LLM provider: {provider_name}")
                return llm.generate(prompt, system_message, max_tokens)
            except Exception as exc:
                logger.warning(
                    f"LLM provider '{provider_name}' failed: {exc}. Trying next fallback..."
                )
                last_exc = exc

        if last_exc:
            raise last_exc
        raise RuntimeError("No LLM providers available")


def _sanitize_key(key: str | None) -> str:
    if not key:
        return ""
    stripped = key.encode("ascii", "ignore").decode("ascii").strip()
    if stripped == "••••••••":
        return ""
    return stripped


def get_llm(provider: str | None = None) -> BaseLLM:
    """Factory method to get an LLM instance based on dynamic settings or .env"""
    dynamic_settings = _load()
    api_keys = dynamic_settings.get("api_keys", {})

    groq_key = _sanitize_key(api_keys.get("groq") or settings.GROQ_API_KEY)
    openrouter_key = _sanitize_key(api_keys.get("openrouter") or settings.OPENROUTER_API_KEY)
    gemini_key = _sanitize_key(api_keys.get("gemini") or settings.GEMINI_API_KEY)

    provider = provider or dynamic_settings.get("llm_provider") or settings.LLM_PROVIDER or getattr(settings, "DEFAULT_LLM_PROVIDER", "groq")
    if provider:
        provider = provider.strip().lower()
    # 'mock' is always valid; unknown providers fall back to litellm
    if provider not in VALID_PROVIDERS:
        logger.warning("Unknown provider '%s', falling back to litellm", provider)
        provider = "litellm"

    if provider == "mock":
        from app.llm.providers.mock_llm import MockLLM
        return MockLLM()

    # Build the fallback map of available configured providers
    providers_map = {}
    if groq_key:
        providers_map["groq"] = GroqLLM(api_key=groq_key)
    if gemini_key:
        providers_map["gemini"] = GeminiLLM(api_key=gemini_key)
    if openrouter_key:
        providers_map["openrouter"] = OpenRouterLLM(api_key=openrouter_key)
    # Azure is always available if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
        try:
            providers_map["azure"] = AzureOpenAILLM()
        except Exception as exc:
            logger.warning("Failed to initialize AzureOpenAILLM: %s", exc)

    primary = provider
    if primary not in providers_map:
        if providers_map:
            primary = list(providers_map.keys())[0]
        else:
            # No API keys, use mock
            from app.llm.providers.mock_llm import MockLLM
            return MockLLM()

    return FallbackLLM(primary_provider=primary, providers_map=providers_map)