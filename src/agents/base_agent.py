"""
Base agent class for the text2query system.

Provides common functionality for all agents in the workflow.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from lib.agent import ModelWrapper
from models.models import AgentState, AgentResult, AgentType
from utils.logging import log_ai_response


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the text2query system."""
    
    def __init__(self, agent_type: AgentType, model_wrapper: ModelWrapper):
        """Initialize the base agent."""
        self.agent_type = agent_type
        self.model_wrapper = model_wrapper
        self.name = agent_type.value.replace("_", " ").title()
    
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
    
    def update_state(self, state: AgentState, updates: Dict[str, Any]) -> None:
        """Update the state with new information."""
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
                logger.debug(f"Updated state.{key} = {value}")
            else:
                logger.warning(f"Attempted to update non-existent state field: {key}")
    
    def generate_with_llm(self, schema_class=None, system_message: str = None, human_message: str = None, tools: list = None, **kwargs):
        """Generate text using the model with standardized logging and params.

        Args:
            schema_class: Pydantic model class for structured output (optional)
            system_message: System prompt/instruction (optional)
            human_message: User/human message
            **kwargs: Additional generation parameters

        Returns:
            Instance of the Pydantic schema class or plain text string

        """
        try:
            response = self.model_wrapper.generate(
                schema_class=schema_class,
                system_message=system_message,
                human_message=human_message,
                tools=tools,
                **kwargs
            )
            log_ai_response(logger, self.name, response)
            return response
        except Exception as e:
            logger.error(f"LLM generation failed in {self.name}: {e}")
            raise
