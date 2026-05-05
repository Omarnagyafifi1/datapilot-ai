from app.llm.base_llm import BaseLLM

try:
    from langchain_openrouter import ChatOpenRouter
except Exception:
    ChatOpenRouter = None


class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        if ChatOpenRouter is None:
            raise RuntimeError("OpenRouter LLM provider is not installed in this environment")
        self.api_key = api_key
        self.llm = ChatOpenRouter(
            model="google/gemma-4-31b-it:free",
            openrouter_api_key=api_key
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
