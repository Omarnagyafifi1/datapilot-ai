from app.llm.base_llm import BaseLLM
from langchain_openrouter import ChatOpenRouter

class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self.llm = ChatOpenRouter(
            model="google/gemma-4-31b-it:free", 
            openrouter_api_key=api_key
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
