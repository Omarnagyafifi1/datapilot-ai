from app.core.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.providers.groq_llm import GroqLLM
from app.llm.providers.openrouter_llm import OpenRouterLLM
from app.llm.providers.gemini_llm import GeminiLLM
from app.llm.providers.lite_llm import LiteLLMProvider
from app.services.settings_service import _load
from app.core.logger import get_logger
from typing import Optional, Any

<<<<<<< HEAD
# Optional LLM providers - import only if available
try:
    from app.llm.providers.openai_llm import OpenAILLM
except ImportError:
    OpenAILLM = None

try:
    from app.llm.providers.anthropic_llm import AnthropicLLM
except ImportError:
    AnthropicLLM = None

try:
    from app.llm.providers.deepseek_llm import DeepSeekLLM
except ImportError:
    DeepSeekLLM = None

try:
    from app.llm.providers.together_llm import TogetherLLM
except ImportError:
    TogetherLLM = None

try:
    from app.llm.providers.ollama_llm import OllamaLLM
except ImportError:
    OllamaLLM = None

# LLM settings service - fallback to empty settings if not available
try:
    from app.services.llm_settings_service import get_llm_settings
except ImportError:
    def get_llm_settings():
        return {}


def get_llm(
    provider: str = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    api_keys: dict = None,
) -> BaseLLM:
    """
    Get LLM instance based on provider and configuration.
    
    If provider is not specified, uses runtime settings from database or falls back to .env defaults.
    """
    # Get runtime settings if not explicitly provided
    runtime_settings = get_llm_settings()
    
    provider = provider or runtime_settings.get("provider", settings.DEFAULT_LLM_PROVIDER)
    model = model or runtime_settings.get("model", settings.DEFAULT_LLM_MODEL)
    temperature = temperature if temperature is not None else runtime_settings.get("temperature", 0.2)
    max_tokens = max_tokens or runtime_settings.get("max_tokens", 2048)
    api_keys = api_keys or runtime_settings.get("api_keys", {})
    
    if provider == "groq":
        return GroqLLM(
            api_key=api_keys.get("groq") or settings.GROQ_API_KEY,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "openrouter":
        return OpenRouterLLM(
            api_key=api_keys.get("openrouter") or settings.OPENROUTER_API_KEY,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "gemini":
        return GeminiLLM(
            api_key=api_keys.get("gemini") or settings.GEMINI_API_KEY,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "openai":
        if OpenAILLM is None:
            return MockLLM()
        return OpenAILLM(
            api_key=api_keys.get("openai") or settings.OPENAI_API_KEY,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "anthropic":
        if AnthropicLLM is None:
            return MockLLM()
        return AnthropicLLM(
            api_key=api_keys.get("anthropic") or settings.ANTHROPIC_API_KEY,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "deepseek":
        if DeepSeekLLM is None:
            return MockLLM()
        return DeepSeekLLM(
            api_key=api_keys.get("deepseek") or settings.DEEPSEEK_API_KEY,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "together":
        if TogetherLLM is None:
            return MockLLM()
        return TogetherLLM(
            api_key=api_keys.get("together") or settings.TOGETHER_API_KEY,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "ollama":
        if OllamaLLM is None:
            return MockLLM()
        return OllamaLLM(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        # Fallback to mock for unknown/missing providers
        return MockLLM()
=======
from functools import lru_cache

logger = get_logger(__name__)

VALID_PROVIDERS = {"groq", "openrouter", "gemini", "litellm", "mock"}


class FallbackLLM(BaseLLM):
    def __init__(self, primary_provider: str, providers_map: dict[str, BaseLLM]) -> None:
        self.primary_provider = primary_provider
        self.providers_map = providers_map

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        # Determine fallback order starting with the primary provider
        order = [self.primary_provider]
        for p in ["groq", "gemini", "openrouter"]:
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


@lru_cache(maxsize=8)
def _get_cached_llm(provider: str, groq_key: str, openrouter_key: str, gemini_key: str) -> BaseLLM:
    if provider == "groq":
        return GroqLLM(api_key=groq_key)
    elif provider == "openrouter":
        return OpenRouterLLM(api_key=openrouter_key)
    elif provider == "gemini":
        return GeminiLLM(api_key=gemini_key)
    elif provider == "litellm":
        return LiteLLMProvider(api_keys={"groq": groq_key, "openrouter": openrouter_key, "gemini": gemini_key})
    elif provider == "mock":
        from app.llm.providers.mock_llm import MockLLM
        return MockLLM()
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
    # 'mock' is always valid; unknown providers fall back to litellm
    if provider not in VALID_PROVIDERS:
        logger.warning("Unknown provider '%s', falling back to litellm", provider)
        provider = "litellm"

    if provider == "mock":
        return _get_cached_llm("mock", groq_key, openrouter_key, gemini_key)

    # Build the fallback map of available configured providers
    providers_map = {}
    if groq_key:
        providers_map["groq"] = _get_cached_llm("groq", groq_key, openrouter_key, gemini_key)
    if gemini_key:
        providers_map["gemini"] = _get_cached_llm("gemini", groq_key, openrouter_key, gemini_key)
    if openrouter_key:
        providers_map["openrouter"] = _get_cached_llm("openrouter", groq_key, openrouter_key, gemini_key)

    primary = provider
    if primary not in providers_map:
        if providers_map:
            primary = list(providers_map.keys())[0]
        else:
            return _get_cached_llm(provider, groq_key, openrouter_key, gemini_key)

    return FallbackLLM(primary_provider=primary, providers_map=providers_map)
>>>>>>> main
