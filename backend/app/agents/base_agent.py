from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    @abstractmethod
    def run(self, question: str, source_id: str) -> dict[str, Any]:
        """Execute an agent flow."""
