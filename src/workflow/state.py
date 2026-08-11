"""State-update utilities for the Text2Query workflow."""

from models.models import AgentState


class StateManager:
    """Utilities for managing agent state updates."""

    @staticmethod
    def update_state_with_preservation(state: AgentState, updates: dict) -> None:
        """Update state while preserving critical system fields."""
        system_fields_to_preserve = ["retries_left", "is_query_valid"]

        # Only preserve system fields that are NOT being updated by the agent
        preserved_values = {}
        for field in system_fields_to_preserve:
            if hasattr(state, field) and field not in updates:
                preserved_values[field] = getattr(state, field)

        # Apply agent updates
        for key, value in updates.items():
            setattr(state, key, value)

        # Restore preserved system fields (only those not updated by agent)
        for field, value in preserved_values.items():
            setattr(state, field, value)
