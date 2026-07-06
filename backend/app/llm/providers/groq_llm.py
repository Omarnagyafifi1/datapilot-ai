from app.llm.base_llm import BaseLLM
from app.core.config import settings
from typing import Optional

# Use OpenAI-compatible client for Groq
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str = "", model: str | None = None) -> None:
        if OpenAI is None:
            raise RuntimeError("OpenAI client is not installed in this environment")
        self.api_key = api_key or settings.GROQ_API_KEY or ""
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=30.0,
        )
        self.model = model or "llama-3.3-70b-versatile"

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        kwargs = {"model": self.model, "messages": messages, "temperature": 0.0, "max_tokens": max_tokens or 1024}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""