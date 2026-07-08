from __future__ import annotations

from typing import Optional

from openai import AzureOpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.llm.base_llm import BaseLLM

logger = get_logger(__name__)


class AzureOpenAILLM(BaseLLM):
    """Azure OpenAI (AI Foundry) LLM provider."""

    def __init__(self) -> None:
        endpoint = (settings.AZURE_OPENAI_ENDPOINT or "").strip()
        api_key = (settings.AZURE_OPENAI_API_KEY or "").strip()
        deployment = (settings.AZURE_OPENAI_DEPLOYMENT or "gpt-4o").strip()
        api_version = (settings.AZURE_OPENAI_API_VERSION or "2024-02-15-preview").strip()

        if not endpoint or not api_key:
            raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

        self.deployment = deployment
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        logger.info(
            "AzureOpenAILLM initialized (deployment=%s, endpoint=%s)",
            deployment,
            endpoint.split("/")[2] if "//" in endpoint else "configured",
        )

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.deployment,
            "messages": messages,
            "max_completion_tokens": max_tokens or 1024,
        }

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
