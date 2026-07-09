from __future__ import annotations

from typing import Optional

from openai import OpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.llm.base_llm import BaseLLM

logger = get_logger(__name__)


class AzureOpenAILLM(BaseLLM):
    """Azure OpenAI (AI Foundry) LLM provider.

    Supports both:
      - Standard Azure OpenAI: https://{resource}.openai.azure.com/
      - AI Foundry serverless: https://{project}.services.ai.azure.com/openai/v1
    """

    def __init__(self) -> None:
        base_url = (settings.AZURE_OPENAI_ENDPOINT or "").strip()
        api_key = (settings.AZURE_OPENAI_API_KEY or "").strip()
        deployment = (settings.AZURE_OPENAI_DEPLOYMENT or "gpt-4o").strip()

        if not base_url or not api_key:
            raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

        # If the URL ends with /openai/v1 (AI Foundry serverless), use it as
        # a regular OpenAI-compatible base_url with the deployment as model.
        if base_url.rstrip("/").endswith("/openai/v1"):
            self._use_azure_sdk = False
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._use_azure_sdk = True
            from openai import AzureOpenAI
            api_version = (settings.AZURE_OPENAI_API_VERSION or "2024-02-15-preview").strip()
            self.client = AzureOpenAI(
                azure_endpoint=base_url.rstrip("/"),
                api_key=api_key,
                api_version=api_version,
            )

        self.deployment = deployment
        logger.info(
            "AzureOpenAILLM initialized (deployment=%s, mode=%s, endpoint=%s)",
            deployment,
            "foundry" if not self._use_azure_sdk else "azure",
            base_url.split("/")[2] if "//" in base_url else "configured",
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
        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        if msg.content:
            return msg.content
        if msg.refusal:
            logger.warning("Azure OpenAI refused (finish=%s): %s", finish_reason, msg.refusal[:200])
            return ""
        logger.warning("Azure OpenAI returned empty content (finish=%s)", finish_reason)
        return ""
