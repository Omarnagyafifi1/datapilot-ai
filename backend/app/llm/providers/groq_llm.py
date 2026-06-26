from app.llm.base_llm import BaseLLM
from app.core.config import settings

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        if ChatGroq is None:
            raise RuntimeError("Groq LLM provider is not installed in this environment")
        self.api_key = api_key
        model_name = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        self.llm = ChatGroq(
            model=model_name,
            groq_api_key=api_key
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content


