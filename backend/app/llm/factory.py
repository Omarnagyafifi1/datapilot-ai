from app.core.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.providers.mock_llm import MockLLM
from app.llm.providers.openai_llm import OpenAILLM


def get_llm(provider: str = "mock") -> BaseLLM:
    if provider == "openai":
        return OpenAILLM(api_key=settings.groq_api_key)
    return MockLLM()
