from app.llm.base_llm import BaseLLM
from langchain_groq import ChatGroq

class GroqLLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            groq_api_key=api_key
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
