from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Abstract base for all agents."""

    @abstractmethod
    def run(self, input_text: str) -> str:
        pass
