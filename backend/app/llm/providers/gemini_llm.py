from app.llm.base_llm import BaseLLM
from langchain_google_genai import ChatGoogleGenerativeAI

class GeminiLLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=api_key
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
