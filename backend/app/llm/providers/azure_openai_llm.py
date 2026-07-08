from app.llm.base_llm import BaseLLM
from typing import Optional

try:
    from openai import OpenAI, AzureOpenAI
except ImportError:
    OpenAI = None
    AzureOpenAI = None


class AzureOpenAILLM(BaseLLM):
    def __init__(
        self,
        endpoint: str = "",
        api_key: str = "",
        deployment: str | None = None,
        api_version: str | None = None,
        use_entra_id: bool = False,
    ) -> None:
        if OpenAI is None:
            raise RuntimeError("OpenAI client is not installed in this environment")
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment or ""
        self.api_version = api_version or "2024-02-15-preview"
        self.use_entra_id = use_entra_id

        # If endpoint contains /openai/v1 (AI Foundry style), use standard OpenAI client
        if "/openai/v1" in endpoint:
            if use_entra_id or not api_key:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://ai.azure.com/.default"
                )
                self.client = OpenAI(
                    base_url=endpoint,
                    api_key=token_provider,
                    timeout=60.0,
                )
            else:
                self.client = OpenAI(
                    base_url=endpoint,
                    api_key=api_key,
                    timeout=60.0,
                )
        else:
            # Standard Azure OpenAI endpoint
            if AzureOpenAI is None:
                raise RuntimeError("AzureOpenAI client is not installed in this environment")
            if use_entra_id or not api_key:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
                self.client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=api_version,
                    timeout=60.0,
                )
            else:
                self.client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version,
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
            "max_completion_tokens": max_tokens or 1024,
        }
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
