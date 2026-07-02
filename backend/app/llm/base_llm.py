from abc import ABC, abstractmethod
from typing import Optional


class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        """Generate text from a prompt."""
