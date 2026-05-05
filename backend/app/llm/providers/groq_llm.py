from app.llm.base_llm import BaseLLM

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        if ChatGroq is None:
            raise RuntimeError("Groq LLM provider is not installed in this environment")
        self.api_key = api_key
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=api_key
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
