from app.llm.base_llm import BaseLLM
from app.core.config import settings

try:
    from langchain_openrouter import ChatOpenRouter
except Exception:
    ChatOpenRouter = None


class OpenRouterLLM(BaseLLM):
    def __init__(
        self,
        api_key: str = "",
        model: str = "google/gemma-4-31b-it:free",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        if ChatOpenRouter is None:
            raise RuntimeError("OpenRouter LLM provider is not installed in this environment")
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = ChatOpenRouter(
            model=model,
            openrouter_api_key=self.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
