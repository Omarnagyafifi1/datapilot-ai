from app.llm.base_llm import BaseLLM
from app.core.config import settings
from typing import Optional
from openai import OpenAI


class GroqLLM(BaseLLM):
<<<<<<< HEAD
    def __init__(
        self,
        api_key: str = "",
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        if ChatGroq is None:
            raise RuntimeError("Groq LLM provider is not installed in this environment")
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = ChatGroq(
            model=model,
            groq_api_key=self.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
=======
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        model_name = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        self.model = model_name
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=30.0,
>>>>>>> main
        )

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        kwargs = {"model": self.model, "messages": messages, "temperature": 0.0, "max_tokens": max_tokens or 1024}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


