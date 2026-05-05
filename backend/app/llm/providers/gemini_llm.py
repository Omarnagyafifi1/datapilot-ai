from app.llm.base_llm import BaseLLM

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None


class GeminiLLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("Gemini LLM provider is not installed in this environment")
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
