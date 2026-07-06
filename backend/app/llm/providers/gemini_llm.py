from app.llm.base_llm import BaseLLM
from app.core.config import settings
from typing import Optional

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None


class GeminiLLM(BaseLLM):
    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-2.5-flash",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("Gemini LLM provider is not installed in this environment")
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self.api_key,
            temperature=temperature,
            timeout=30,
            max_output_tokens=max_tokens,
        )

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        kwargs = {}
        if max_tokens:
            kwargs["max_output_tokens"] = max_tokens
        response = self.llm.invoke(messages, **kwargs)
        return response.content