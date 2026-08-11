"""
LangChain Ollama Integration

A wrapper that uses LangChain's Ollama integration with custom JSON parsing for structured outputs
and tool calling support
"""

import logging
from typing import Optional

from langchain_ollama import ChatOllama

from .chat_wrapper_base import LangChainChatWrapperBase

# Configure logging
logger = logging.getLogger(__name__)


class LangChainOllamaWrapper(LangChainChatWrapperBase):
    """
    LangChain-based Ollama wrapper that provides a clean interface
    while leveraging LangChain's Ollama integration.
    """

    def __init__(
        self,
        model: str = "gpt-oss:20b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.6,
        top_p: float = 0.95,
        timeout: int = 300,
        **kwargs,
    ):
        """
        Initialize the LangChain Ollama wrapper.

        Args:
            model: Ollama model name
            base_url: Ollama API base URL
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            timeout: Request timeout in seconds
            **kwargs: Additional ChatOllama parameters
        """
        super().__init__(
            model=model,
            base_url=base_url,
            temperature=temperature,
            top_p=top_p,
            timeout=timeout,
            **kwargs,
        )

    def _build_llm(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        filter_keys: Optional[set] = None,
        **kwargs,
    ) -> ChatOllama:
        """Create a ChatOllama with consistent defaults and optional kwargs filtering."""
        filtered_kwargs = kwargs
        if filter_keys:
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in filter_keys}

        return ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=temperature,
            top_p=top_p,
            timeout=self.timeout,
            **filtered_kwargs,
        )
