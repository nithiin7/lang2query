from typing import Optional

from .base_agent import BaseAgent


class SampleAgent(BaseAgent):
    """A simple sample agent that echoes the input."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def run(self, input_text: str) -> str:
        """Echo the input text for now."""
        return f"Sample agent received: {input_text}"
