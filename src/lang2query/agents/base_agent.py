"""
Base agent class for the text2query system.

Provides common functionality for all agents in the workflow.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from lang2query.models.wrapper import ModelWrapper

from .models import AgentMessage, AgentResult, AgentState, AgentType

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the text2query system."""

    def __init__(self, agent_type: AgentType, model_wrapper: ModelWrapper):
        """
        Initialize the base agent.

        Args:
            agent_type: Type of this agent
            model_wrapper: Model wrapper for text generation
        """
        self.agent_type = agent_type
        self.model_wrapper = model_wrapper
        self.name = agent_type.value.replace("_", " ").title()

        logger.info(f"Initialized {self.name} agent")

    @abstractmethod
    def process(self, state: AgentState) -> AgentResult:
        """
        Process the current state and return results.

        Args:
            state: Current agent state

        Returns:
            AgentResult with processing results
        """
        pass

    def add_message(
        self,
        state: AgentState,
        content: str,
        receiver: AgentType,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to the agent communication log.

        Args:
            state: Current state to update
            content: Message content
            receiver: Target agent for the message
            data: Optional additional data
        """
        message = AgentMessage(
            sender=self.agent_type, receiver=receiver, content=content, data=data
        )
        state.agent_messages.append(message)
        logger.debug(f"{self.name} -> {receiver.value}: {content}")

    def update_state(self, state: AgentState, updates: Dict[str, Any]) -> None:
        """
        Update the state with new information.

        Args:
            state: State to update
            updates: Dictionary of updates to apply
        """
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
                logger.debug(f"Updated state.{key} = {value}")
            else:
                logger.warning(f"Attempted to update non-existent state field: {key}")

    def generate_with_llm(self, prompt: str, **kwargs) -> str:
        """
        Generate text using the model wrapper.

        Args:
            prompt: Input prompt
            **kwargs: Generation parameters

        Returns:
            Generated text
        """
        try:
            return self.model_wrapper.generate(prompt, **kwargs)
        except Exception as e:
            logger.error(f"LLM generation failed in {self.name}: {e}")
            raise

    def log_processing_start(self, state: AgentState) -> None:
        """Log the start of processing."""
        logger.info(
            f"{self.name} starting to process: {state.natural_language_query[:100]}..."
        )

    def log_processing_end(self, state: AgentState, result: AgentResult) -> None:
        """Log the end of processing."""
        status = "✅" if result.success else "❌"
        logger.info(f"{self.name} processing complete: {status} {result.message}")
