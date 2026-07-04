from app.llm.base_llm import BaseLLM
from app.core.config import settings
from typing import Optional
from openai import OpenAI


class GroqLLM(BaseLLM):
    def __init__(
        self,
        api_key: str = "",
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or getattr(settings, 'GROQ_MODEL', None) or "llama-3.3-70b-versatile"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        limit_tokens = max_tokens or self.max_tokens
        if limit_tokens:
            kwargs["max_tokens"] = limit_tokens
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
