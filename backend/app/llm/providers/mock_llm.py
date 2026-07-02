from app.llm.base_llm import BaseLLM
from typing import Optional

class MockLLM(BaseLLM):
    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        if "intent classification engine" in prompt.lower():
            return "ADD"
        return f"Mock response for: {prompt}"
