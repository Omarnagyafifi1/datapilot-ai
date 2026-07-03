from app.core.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.providers.mock_llm import MockLLM
from app.llm.providers.groq_llm import GroqLLM
from app.llm.providers.openrouter_llm import OpenRouterLLM
from app.llm.providers.gemini_llm import GeminiLLM

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
