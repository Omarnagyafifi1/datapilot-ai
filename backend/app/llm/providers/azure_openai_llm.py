from app.llm.base_llm import BaseLLM
from typing import Optional

try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None


class AzureOpenAILLM(BaseLLM):
    def __init__(
        self,
        endpoint: str = "",
        api_key: str = "",
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        if AzureOpenAI is None:
            raise RuntimeError("OpenAI client is not installed in this environment")
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment or ""
        self.api_version = api_version or "2024-02-15-preview"
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            timeout=60.0,
        )

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        kwargs = {
            "model": self.deployment,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_tokens or 1024,
        }
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
