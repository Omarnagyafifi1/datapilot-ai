from app.llm.base_llm import BaseLLM
from typing import Optional

# Use OpenAI-compatible client for OpenRouter
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str = "", model: str | None = None) -> None:
        if OpenAI is None:
            raise RuntimeError("OpenAI client is not installed in this environment")
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "DataPilot AI",
            },
            timeout=30.0,
        )
        self.model = model or "google/gemma-4-31b-it:free"

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        kwargs = {"model": self.model, "messages": messages, "temperature": 0.0, "max_tokens": max_tokens or 1024}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""