from app.llm.base_llm import BaseLLM
from app.core.config import settings

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None


class GeminiLLM(BaseLLM):
    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-2.5-flash",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("Gemini LLM provider is not installed in this environment")
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
