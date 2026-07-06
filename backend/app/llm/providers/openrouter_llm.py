from app.llm.base_llm import BaseLLM
<<<<<<< HEAD
from app.core.config import settings

try:
    from langchain_openrouter import ChatOpenRouter
except Exception:
    ChatOpenRouter = None


class OpenRouterLLM(BaseLLM):
    def __init__(
        self,
        api_key: str = "",
        model: str = "google/gemma-4-31b-it:free",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        if ChatOpenRouter is None:
            raise RuntimeError("OpenRouter LLM provider is not installed in this environment")
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = ChatOpenRouter(
            model=model,
            openrouter_api_key=self.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
=======
from openai import OpenAI


class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str = "", model: str | None = None) -> None:
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "DataPilot AI",
            },
            timeout=30.0,
>>>>>>> main
        )
        self.model = model or "google/gemma-4-31b-it:free"

    def generate(self, prompt: str, system_message: str | None = None, max_tokens: int | None = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        kwargs = {"model": self.model, "messages": messages, "temperature": 0.0, "max_tokens": max_tokens or 1024}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
