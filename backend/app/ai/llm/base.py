"""
Shared LangChain Chat Wrapper Base

Defines the contract every LangChain chat-model wrapper (ChatGPT, Ollama, ...)
subclasses: construction and provider-specific `_build_llm`, plus the public
`generate()` entry point. Message building, the tool-calling loop, and
structured JSON parsing live in `GenerationEngine` (see generation.py) and are
invoked here by composition rather than owned by this class.
"""

import logging
from typing import List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import BaseTool

from .generation import GenerationEngine

# Configure logging
logger = logging.getLogger(__name__)


class LangChainChatWrapperBase:
    """
    Base class for LangChain-based chat model wrappers.

    Subclasses must implement `_build_llm` to construct their provider-specific
    chat model (e.g. ChatOpenAI, ChatOllama). Everything else - the unified
    `generate` entry point and the generation strategies it dispatches to -
    is shared via `GenerationEngine`.
    """

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        temperature: float = 0.6,
        top_p: float = 0.95,
        timeout: int = 300,
        **kwargs,
    ):
        self.model_name = model
        self.base_url = base_url
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout

        self.llm = self._build_llm(temperature=temperature, top_p=top_p, **kwargs)
        self.output_parser = StrOutputParser()
        self.generation_chain = self.llm | self.output_parser

    def _build_llm(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        filter_keys: Optional[set] = None,
        **kwargs,
    ):
        """Construct the provider-specific chat model instance. Implemented by subclasses."""
        raise NotImplementedError

    def _create_llm(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        filter_keys: Optional[set] = None,
        **kwargs,
    ):
        """Create a chat model with consistent defaults and optional kwargs filtering."""
        return self._build_llm(
            temperature=temperature if temperature is not None else self.temperature,
            top_p=top_p if top_p is not None else self.top_p,
            filter_keys=filter_keys,
            **kwargs,
        )

    def generate(
        self,
        prompt: Optional[str] = None,
        human_message: Optional[str] = None,
        system_message: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        schema_class: Optional[type] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ):
        """
        Unified generate method supporting basic text, tool-enabled, and structured output generation.
        Structured outputs via format parameter, tool calling via tools parameter.

        Args:
            prompt: Input text prompt (used as human message)
            human_message: Human message content
            system_message: Optional system prompt/instruction
            tools: Optional list of LangChain tools for function calling
            schema_class: Optional Pydantic model class for structured output
            temperature: Sampling temperature (set to 0 for structured outputs)
            top_p: Top-p sampling parameter
            **kwargs: Additional generation parameters

        Returns:
            Generated text string or structured object (depending on schema_class)
        """
        try:
            message = human_message or prompt
            if not message:
                raise ValueError("Either prompt or human_message must be provided")

            # Route to appropriate generation strategy based on parameters
            if tools is not None and schema_class is not None:
                return GenerationEngine.generate_with_tools_and_structure(
                    create_llm=self._create_llm,
                    system_message=system_message,
                    human_message=message,
                    tools=tools,
                    schema_class=schema_class,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs,
                )
            elif tools is not None:
                return GenerationEngine.generate_with_tools(
                    create_llm=self._create_llm,
                    system_message=system_message,
                    human_message=message,
                    tools=tools,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs,
                )
            elif schema_class is not None:
                return GenerationEngine.generate_structured(
                    create_llm=self._create_llm,
                    schema_class=schema_class,
                    system_message=system_message,
                    human_message=message,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs,
                )
            else:
                return GenerationEngine.generate_basic(
                    create_llm=self._create_llm,
                    output_parser=self.output_parser,
                    generation_chain=self.generation_chain,
                    prompt=message,
                    system_message=system_message,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs,
                )

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
