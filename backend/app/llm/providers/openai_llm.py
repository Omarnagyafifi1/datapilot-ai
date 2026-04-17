from app.llm.base_llm import BaseLLM


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        return "OpenAI provider placeholder response"
