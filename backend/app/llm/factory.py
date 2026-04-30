from app.core.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.providers.mock_llm import MockLLM
from app.llm.providers.groq_llm import GroqLLM
from app.llm.providers.openrouter_llm import OpenRouterLLM
from app.llm.providers.gemini_llm import GeminiLLM

def get_llm(provider: str = "mock") -> BaseLLM:
    if provider == "groq":
        return GroqLLM(api_key=settings.GROQ_API_KEY)
    elif provider == "openrouter":
        return OpenRouterLLM(api_key=settings.OPENROUTER_API_KEY)
    elif provider == "gemini":
        return GeminiLLM(api_key=settings.GEMINI_API_KEY)
    if provider == "openai":
        return MockLLM()
    return MockLLM()
