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

    @staticmethod
    def apply_hitl_feedback(state: AgentState, feedback: dict) -> None:
        """Apply human-in-the-loop approval/edit feedback to workflow state."""
        review_type = (feedback.get("review_type") or "").strip()
        action = (feedback.get("action") or "").strip().lower()
        approved_items = feedback.get("approved_items") or []
        feedback_text = feedback.get("feedback_text")

        if review_type not in ("databases", "tables"):
            return

        approvals = dict(getattr(state, "human_approvals", {}) or {})
        approvals[review_type] = action == "approve"
        state.human_approvals = approvals
        state.human_feedback = feedback_text

        if approved_items:
            setattr(state, f"relevant_{review_type}", approved_items)
