from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    def run(self, question: str) -> str:
        """Execute an agent flow."""
