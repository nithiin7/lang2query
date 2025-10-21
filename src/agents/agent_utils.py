"""
Common utilities for all agents in the text2query system.

This module contains shared functionality that is used across multiple agents
to ensure consistency and reduce code duplication.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from models.models import AgentResult, AgentState

logger = logging.getLogger(__name__)


class AgentUtils:
    """Common utilities shared across all agents."""

    @staticmethod
    def create_error_result(message: str) -> AgentResult:
        """Create a standardized error result."""
        return AgentResult(success=False, message=message)

    @staticmethod
    def extract_json_text(text: str) -> Optional[str]:
        """
        Extract JSON text from response string.

        Looks for JSON object boundaries and extracts the complete JSON text.
        Handles incomplete JSON by finding the last complete brace.
        """
        if not text or not text.strip():
            return None

        json_start = text.find('{')
        json_end = text.rfind('}')

        if json_start >= 0 and json_end > json_start:
            json_text = text[json_start:json_end + 1]

            # Ensure we have a complete JSON object
            if json_text.endswith('}'):
                return json_text
            else:
                # Try to find the last complete brace
                last_brace = json_text.rfind('}')
                if last_brace > 0:
                    return json_text[:last_brace + 1]

        return None

    @staticmethod
    def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from response text with fallback handling.

        Returns the parsed JSON object or None if parsing fails.
        """
        try:
            json_text = AgentUtils.extract_json_text(text)
            if json_text:
                return json.loads(json_text)
        except ValueError as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
        return None

    @staticmethod
    def get_validation_feedback_section(state: AgentState) -> str:
        """Get standardized validation feedback section for prompts."""
        feedback = getattr(state, 'query_validation_feedback', None) or {}
        if not feedback.get("overall_valid", True):
            reason = feedback.get("reason") or feedback.get("llm_judgment")
            if reason:
                return f"""Context From Previous Validation:
                The last generated query was judged INVALID because: "{reason}".
                Consider this when constructing your response."""
        return ""

    @staticmethod
    def validate_state_prerequisites(state: AgentState, required_fields: List[str]) -> Optional[AgentResult]:
        """
        Validate that required state fields are present.

        Args:
            state: Current agent state
            required_fields: List of field names that must be present and non-empty

        Returns:
            AgentResult if validation fails, None if validation passes
        """
        for field in required_fields:
            value = getattr(state, field, None)
            if value is None or (isinstance(value, (list, str)) and not value):
                return AgentUtils.create_error_result(f"Missing required field: {field}")

        return None

    @staticmethod
    def validate_query_text(state: AgentState) -> Optional[AgentResult]:
        """Validate that the query text is present and non-empty."""
        if not state.natural_language_query or not state.natural_language_query.strip():
            return AgentUtils.create_error_result("No query provided for processing")
        return None

    @staticmethod
    def validate_multiple_fields(state: AgentState, field_checks: List[tuple[str, str]]) -> Optional[AgentResult]:
        """
        Validate multiple state fields with custom error messages.

        Args:
            state: Current agent state
            field_checks: List of tuples (field_name, error_message)

        Returns:
            AgentResult if validation fails, None if validation passes
        """
        for field_name, error_message in field_checks:
            if not getattr(state, field_name, None):
                logger.warning(f"⚠️ {error_message}")
                return AgentUtils.create_error_result(error_message)

        return None

    @staticmethod
    def normalize_list_items(items: List[str], case_sensitive: bool = False) -> List[str]:
        """Normalize list items by stripping whitespace and handling duplicates."""
        if not items:
            return []

        processed = []
        seen = set()

        for item in items:
            normalized = str(item).strip()
            if not case_sensitive:
                normalized_lower = normalized.lower()

            if normalized and (case_sensitive and normalized not in seen) or \
               (not case_sensitive and normalized_lower not in seen):
                processed.append(normalized)
                seen.add(normalized_lower if not case_sensitive else normalized)

        return processed

    @staticmethod
    def build_human_feedback_section(state: AgentState, kind: str) -> str:
        """Build the human feedback/context section for prompts.

        Args:
            state: Current agent state
            kind: One of "database" or "tables" to tailor labels and rules
        """
        kind_lower = (kind or "").strip().lower()

        # Configuration mapping for different kinds
        kind_config = {
            "database": {
                "items_attr": "relevant_databases",
                "label": "Previously Selected Databases",
                "item_type": "databases"
            },
            "tables": {
                "items_attr": "relevant_tables", 
                "label": "Previously Selected Tables",
                "item_type": "tables"
            }
        }
        
        if kind_lower not in kind_config:
            return ""
            
        config = kind_config[kind_lower]
        human_feedback_text = getattr(state, 'human_feedback', None)
        previously_selected_items = getattr(state, config['items_attr'], [])
        previously_label = config['label']
        suffix_note = f"Note: Consider the previously selected {config['item_type']} as a foundation, and user suggestions as recommendations to enhance the selection."

        if not previously_selected_items and not human_feedback_text:
            return ""

        context_text = ""
        if previously_selected_items:
            context_text += f"\n**{previously_label}:** {', '.join(previously_selected_items)}"

        suggestion_text = ""
        if human_feedback_text:
            suggestion_text += f"\n**User Feedback:** {human_feedback_text}"

        if not context_text and not suggestion_text:
            return ""

        return f"""**CONTEXT INFORMATION:**
{context_text}{suggestion_text}

{suffix_note}"""