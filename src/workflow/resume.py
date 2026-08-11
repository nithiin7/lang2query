"""Resume-point resolution for the Text2Query workflow.

Given an `AgentState` captured mid-run (e.g. from a paused WebSocket
session), `ResumeRouter.determine_resume_node` figures out which graph
node execution should continue from. This is state inspection only - it
does not touch the LangGraph `StateGraph` itself.
"""

import logging

from models.models import AgentState

logger = logging.getLogger(__name__)


class ResumeRouter:
    """Determines which workflow node to resume from given a captured state."""

    @staticmethod
    def determine_resume_node(state: AgentState) -> str:
        """
        Determine which node to resume from based on the current state.

        This analyzes the state to find the logical next step in the workflow.
        """
        current_step = getattr(state, 'current_step', '')

        # If workflow completed or failed, no resume needed
        if current_step in ['workflow_completed', 'workflow_failed', 'max_retries_exhausted', 'sql_safety_check_failed']:
            return "end"

        # PRIORITY 1: If there's human feedback to process, route to the appropriate human review agent first
        human_feedback = getattr(state, 'human_feedback', None)
        if human_feedback and not current_step.endswith('_completed'):
            # Check which type of review this feedback is for
            approvals = getattr(state, 'human_approvals', {}) or {}

            # If we have database feedback to process and database review not completed, go to database human review
            if ('databases' in approvals or hasattr(state, 'relevant_databases')) and current_step != "database_review_completed":
                return "database_human_review"

            # If we have table feedback to process and table review not completed, go to table human review
            if ('tables' in approvals or hasattr(state, 'relevant_tables')) and current_step != "table_review_completed":
                return "table_human_review"

        # Check for pending human reviews (no feedback yet provided)
        approvals = getattr(state, 'human_approvals', {}) or {}

        # If database review is pending approval, resume from database_human_review
        if not approvals.get('databases', False) and hasattr(state, 'relevant_databases') and state.relevant_databases:
            return "database_human_review"

        # If table review is pending approval, resume from table_human_review
        if not approvals.get('tables', False) and hasattr(state, 'relevant_tables') and state.relevant_tables:
            return "table_human_review"

        # Check current step and determine next logical node
        step_to_node_mapping = {
            "routing_completed": "database_identifier",  # After routing, go to database ID if not metadata
            "database_identification_completed": "table_identifier",
            "database_review_completed": "table_identifier",
            "table_identification_completed": "column_identifier",
            "table_review_completed": "column_identifier",
            "column_identification_completed": "schema_builder",
            "schema_building_completed": "query_planner",
            "query_planning_completed": "query_generator",
            "query_generation_completed": "sql_safety_guard",
            "sql_safety_check_completed": "query_validator",
            "query_validation_completed": "end",
            # Error states - retry from appropriate points
            "database_identification_failed": "database_identifier",
            "table_identifier_failed": "table_identifier",
            "column_identifier_failed": "column_identifier",
            "schema_building_failed": "schema_builder",
            "query_planning_failed": "query_planner",
            "query_generation_failed": "query_generator",
            "sql_safety_guard_failed": "sql_safety_guard",
            "query_validation_failed": "query_validator",
        }

        # Handle validation routing based on validation feedback
        if current_step == "query_validation_completed" and not getattr(state, "is_query_valid", True):
            feedback = getattr(state, "query_validation_feedback", {}) or {}
            issue_type = feedback.get("issue_type") or getattr(state, "last_error_type", None)

            if issue_type == "insufficient_data":
                return "database_identifier"
            elif issue_type == "schema_missing":
                return "table_identifier"
            elif issue_type in ("sql_generation_issue", "data_type_mismatch", "join_relationship_error"):
                return "query_planner"
            else:
                return "database_identifier"  # Default fallback

        # Check for validation retry states
        if current_step.startswith("retry_") or current_step.startswith("route_to_"):
            if "insufficient_data" in current_step:
                return "database_identifier"
            elif "table_identifier" in current_step:
                return "table_identifier"
            elif "query_planner" in current_step:
                return "query_planner"
            elif "database_identifier" in current_step:
                return "database_identifier"

        # Use mapping if available
        if current_step in step_to_node_mapping:
            next_node = step_to_node_mapping[current_step]

            # Special handling for review steps that may have requested changes
            if current_step == "table_review_completed":
                approvals = getattr(state, 'human_approvals', {}) or {}
                if not approvals.get('tables', True):  # If not approved, go back to table identifier
                    return "table_identifier"
            elif current_step == "database_review_completed":
                approvals = getattr(state, 'human_approvals', {}) or {}
                if not approvals.get('databases', True):  # If not approved, go back to database identifier
                    return "database_identifier"

            return next_node

        # Fallback logic based on what data is available
        if hasattr(state, 'generated_query') and state.generated_query:
            return "query_validator"  # If we have a query, validate it
        elif hasattr(state, 'query_plan') and state.query_plan:
            return "query_generator"  # If we have a plan, generate query
        elif hasattr(state, 'schema_context') and state.schema_context:
            return "query_planner"  # If we have schema, plan query
        elif hasattr(state, 'relevant_columns') and state.relevant_columns:
            return "schema_builder"  # If we have columns, build schema
        elif hasattr(state, 'relevant_tables') and state.relevant_tables:
            return "column_identifier"  # If we have tables, find columns
        elif hasattr(state, 'relevant_databases') and state.relevant_databases:
            return "table_identifier"  # If we have databases, find tables
        else:
            return "database_identifier"  # Start from database identification
