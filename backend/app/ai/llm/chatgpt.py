"""
LangChain ChatGPT Integration

A wrapper that uses LangChain's OpenAI integration with custom JSON parsing for structured outputs
and tool calling support
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from .chat_wrapper_base import LangChainChatWrapperBase

# Configure logging
logger = logging.getLogger(__name__)


class LangChainChatGPTWrapper(LangChainChatWrapperBase):
    """
    LangChain-based ChatGPT wrapper that provides a clean interface
    while leveraging LangChain's OpenAI integration.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
        temperature: float = 0.6,
        top_p: float = 0.95,
        timeout: int = 300,
        **kwargs,
    ):
        """
        Initialize the LangChain ChatGPT wrapper.

        Args:
            api_key: OpenAI API key
            model: OpenAI model name (e.g., gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
            base_url: Optional custom base URL for OpenAI-compatible APIs
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            timeout: Request timeout in seconds
            **kwargs: Additional ChatOpenAI parameters
        """
        self.api_key = api_key
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
    ) -> ChatOpenAI:
        """Create a ChatOpenAI with consistent defaults and optional kwargs filtering."""
        filtered_kwargs = kwargs
        if filter_keys:
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in filter_keys}

        return ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            base_url=self.base_url,
            temperature=temperature,
            top_p=top_p,
            timeout=self.timeout,
            **filtered_kwargs,
        )

    def get_model_info(self) -> dict:
        """Get information about the ChatGPT model."""
        return {
            "model_type": "chatgpt",
            "provider": "openai",
            "model": self.model_name,
            "base_url": self.base_url or "https://api.openai.com/v1",
            "chat_format": "openai_compatible",
        }
