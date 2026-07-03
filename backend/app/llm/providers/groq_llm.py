from app.llm.base_llm import BaseLLM
from app.core.config import settings

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None


class GroqLLM(BaseLLM):
    def __init__(
        self,
        api_key: str = "",
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        if ChatGroq is None:
            raise RuntimeError("Groq LLM provider is not installed in this environment")
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = ChatGroq(
            model=model,
            groq_api_key=self.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content


