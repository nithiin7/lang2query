"""Centralized routing and retry-handling logic for the Text2Query workflow.

These functions decide which node the LangGraph `StateGraph` should visit
next given the current `AgentState`. They contain no graph-wiring code
themselves (no `add_node`/`add_edge` calls) - `workflow/graph.py` wires them
in as conditional-edge callbacks.
"""

import logging

from models import AgentState

logger = logging.getLogger(__name__)


class WorkflowRouter:
    """Centralized routing logic for workflow state transitions."""

    @staticmethod
    def check_permanent_failure(
        state: AgentState, step_context: str = "", return_failed_step: bool = False
    ) -> str:
        """
        Check if the current step has permanently failed.

        Args:
            state: Current agent state
            step_context: Optional context for logging (e.g., "Database identifier")
            return_failed_step: If True, return the failed step name instead of END

        Returns:
            END if permanently failed, or the failed step name if return_failed_step=True, empty string if not failed
        """
        from langgraph.graph import END

        current_step = getattr(state, "current_step", "")
        if current_step.endswith("_failed") or current_step.endswith("_error"):
            context_msg = f" {step_context}" if step_context else ""
            logger.error(f"{context_msg} failed permanently")

            if return_failed_step:
                step_name = current_step.replace("_failed", "").replace("_error", "")
                return f"{step_name}_failed"
            else:
                return END

        return ""

    @staticmethod
    def route_after_router(state: AgentState) -> str:
        """Route after router based on query type."""
        # Check if we're resuming - if so, route directly to the resume node
        if getattr(state, "is_resuming", False):
            resume_node = getattr(state, "resume_start_node", "database_identifier")
            logger.info(f"Resuming: Routing directly to {resume_node}")
            return resume_node

        if getattr(state, "is_metadata_query", False):
            logger.info("Routing to metadata agent for metadata query")
            return "metadata_agent"
        else:
            logger.info("Routing to database identifier for data query")
            return "database_identifier"

    @staticmethod
    def _route_after_identifier_step(
        state: AgentState,
        step_context: str,
        step_name: str,
        review_node: str,
        next_node: str,
    ) -> str:
        """Shared routing after an identifier step (database/table): checks for
        permanent failure or a pending retry, then routes based on interaction mode.
        """
        # Check if step failed permanently
        failure_result = WorkflowRouter.check_permanent_failure(state, step_context)
        if failure_result:
            return failure_result

        # Check if this step needs to be retried (only for actual step failures, not resumes)
        if getattr(state, "last_error_type", None) == "step_retry" and not getattr(
            state, "is_resuming", False
        ):
            logger.info(f"Retrying {step_context.lower()} step")
            return step_name

        # Normal routing based on interaction mode
        mode = getattr(state, "interaction_mode", "ask")
        if mode == "interactive":
            logger.info(f"Interactive mode: Routing to {review_node.replace('_', ' ')}")
            return review_node
        else:
            logger.info(
                f"Ask mode: Skipping human review, proceeding to {next_node.replace('_', ' ')}"
            )
            return next_node

    @staticmethod
    def route_after_database_identifier(state: AgentState) -> str:
        """Route after database identifier based on interaction mode and retry status."""
        return WorkflowRouter._route_after_identifier_step(
            state,
            step_context="Database identifier",
            step_name="database_identifier",
            review_node="database_human_review",
            next_node="table_identifier",
        )

    @staticmethod
    def route_after_table_identifier(state: AgentState) -> str:
        """Route after table identifier based on interaction mode and retry status."""
        return WorkflowRouter._route_after_identifier_step(
            state,
            step_context="Table identifier",
            step_name="table_identifier",
            review_node="table_human_review",
            next_node="column_identifier",
        )

    @staticmethod
    def _route_after_identifier_feedback(
        state: AgentState,
        approval_key: str,
        singular_label: str,
        review_node: str,
        next_node: str,
        identifier_node: str,
    ) -> str:
        """Shared routing after human feedback on an identifier step (database/table):
        proceeds if approved, re-shows the review after a modification, or re-runs
        identification on rejection.
        """
        approvals = getattr(state, "human_approvals", {}) or {}
        approved = approvals.get(approval_key, False)

        if approved:
            logger.info(
                f"User approved {approval_key}, proceeding to {next_node.replace('_', ' ')}"
            )
            return next_node

        # Check if we need to show updated list (modifications made) or re-identify
        modification_type = getattr(state, "last_modification_type", None)
        feedback_processed = getattr(state, "feedback_processed", False)

        if feedback_processed and modification_type in ["add", "remove", "modify"]:
            logger.info(
                f"Modifications applied, showing updated {singular_label} list to user"
            )
            # Clear the flag so next iteration doesn't loop
            state.feedback_processed = False
            return review_node
        else:
            logger.info(
                f"User rejected {approval_key}, re-running {singular_label} identification"
            )
            return identifier_node

    @staticmethod
    def route_after_database_human_feedback(state: AgentState) -> str:
        """Route after database human feedback based on approval status and modification type."""
        return WorkflowRouter._route_after_identifier_feedback(
            state,
            approval_key="databases",
            singular_label="database",
            review_node="database_human_review",
            next_node="table_identifier",
            identifier_node="database_identifier",
        )

    @staticmethod
    def route_after_table_human_feedback(state: AgentState) -> str:
        """Route after table human feedback based on approval status and modification type."""
        return WorkflowRouter._route_after_identifier_feedback(
            state,
            approval_key="tables",
            singular_label="table",
            review_node="table_human_review",
            next_node="column_identifier",
            identifier_node="table_identifier",
        )

    @staticmethod
    def route_after_pipeline_step(state: AgentState) -> str:
        """Route after a pipeline step (column_identifier, schema_builder, etc.) checking for retries."""
        # Check if this step needs to be retried
        if getattr(state, "last_error_type", None) == "step_retry":
            current_step = getattr(state, "current_step", "")
            if current_step.endswith("_retry"):
                step_name = current_step.replace("_retry", "")
                logger.info(f"Retrying pipeline step: {step_name}")
                return step_name

        # Check if step failed permanently
        failure_result = WorkflowRouter.check_permanent_failure(state, "Pipeline step")
        if failure_result:
            return failure_result

        # Continue to next step (success case)
        return WorkflowRouter._get_next_step_from_current(state)

    @staticmethod
    def route_after_metadata_step(state: AgentState) -> str:
        """Route after metadata agent step."""
        from langgraph.graph import END

        # Check if this step needs to be retried
        if getattr(state, "last_error_type", None) == "step_retry":
            logger.info("Retrying metadata agent step")
            return "metadata_agent"

        # Check if step failed permanently
        failure_result = WorkflowRouter.check_permanent_failure(state, "Metadata agent")
        if failure_result:
            return failure_result

        # Metadata queries end the workflow
        logger.info("Metadata query completed")
        return END

    @staticmethod
    def _get_next_step_from_current(state: AgentState) -> str:
        """Get the next step based on current step completion."""
        from langgraph.graph import END

        current_step = getattr(state, "current_step", "")

        # Map completion steps to next steps
        next_step_map = {
            "column_identification_completed": "schema_builder",
            "schema_building_completed": "query_planner",
            "query_planning_completed": "query_generator",
            "query_generation_completed": "sql_safety_guard",
        }

        for completion_step, next_step in next_step_map.items():
            if completion_step in current_step:
                return next_step

        # Default fallback
        return END

    @staticmethod
    def route_after_sql_safety_guard(state: AgentState) -> str:
        """Route after the SQL safety guard.

        A precondition error (e.g. no generated query reached this node) is
        retried/failed like any other pipeline step. An actual unsafe-SQL
        verdict is NOT a step failure the retry machinery sees - the agent
        still returns success=True with is_sql_safe=False - so it can never
        be retried or consume step_retries_left; it is always a hard stop.
        """
        from langgraph.graph import END

        # Precondition error on this node (e.g. missing generated_query): reuse
        # the standard pipeline step retry/failure handling.
        if getattr(state, "last_error_type", None) == "step_retry":
            current_step = getattr(state, "current_step", "")
            if current_step.endswith("_retry"):
                logger.info("Retrying SQL safety guard step")
                return "sql_safety_guard"

        failure_result = WorkflowRouter.check_permanent_failure(
            state, "SQL safety guard"
        )
        if failure_result:
            return failure_result

        if getattr(state, "is_sql_safe", False):
            logger.info("SQL safety check passed; proceeding to semantic validation")
            return "query_validator"

        logger.error(
            f"SQL safety check failed: {getattr(state, 'sql_safety_violation', 'unsafe SQL')}. "
            "Hard-stopping (no retry)."
        )
        state.current_step = "sql_safety_check_failed"
        state.user_message = (
            "The generated query was rejected by the read-only safety check and was not "
            f"executed or returned: {getattr(state, 'sql_safety_violation', 'unsafe SQL')}."
        )
        # Do not surface the rejected query to the caller.
        state.generated_query = None
        return END

    @staticmethod
    def route_after_validation(state: AgentState) -> str:
        """Router to decide next step after query validation with diagnostics.

        Rules:
        - If valid: end.
        - If any issues found and retries exhausted: end with last generated query and validation feedback.
        - If feedback indicates missing table/column/schema: route to table_identifier.
        - If SQL generation issue but schema sufficient: route to query_planner.
        - If insufficient data: restart from database_identifier.
        - Otherwise: restart from database_identifier.
        """
        # If valid, end workflow
        if getattr(state, "is_query_valid", False):
            state.current_step = "workflow_completed"
            return "end"

        feedback = getattr(state, "query_validation_feedback", {}) or {}
        issue_type = feedback.get("issue_type") or state.last_error_type

        # Check if we've exhausted retries (retries already decremented in node)
        if state.retries_left <= 0:
            WorkflowRouter._handle_exhausted_retries(state)
            return "end"

        # Route based on issue type (retries already decremented in node if needed)
        if issue_type == "insufficient_data":
            return WorkflowRouter._route_insufficient_data(state)
        elif issue_type == "schema_missing":
            return WorkflowRouter._route_schema_missing(state)
        elif issue_type == "query_scope_issue":
            return WorkflowRouter._route_query_scope_issue(state)
        elif issue_type in (
            "sql_generation_issue",
            "data_type_mismatch",
            "join_relationship_error",
        ):
            return WorkflowRouter._route_sql_issue(state, issue_type)
        else:
            return WorkflowRouter._route_unknown_issue(state, issue_type)

    @staticmethod
    def _route_insufficient_data(state: AgentState) -> str:
        """Handle insufficient data routing."""
        logger.warning(
            "Insufficient data detected; attempting broader re-identification."
        )
        state.current_step = "retry_due_to_insufficient_data"
        return "database_identifier"

    @staticmethod
    def _route_schema_missing(state: AgentState) -> str:
        """Handle schema missing routing."""
        logger.info(
            "Routing to table_identifier due to schema issues (missing tables/columns)"
        )
        state.current_step = "route_to_table_identifier"
        return "table_identifier"

    @staticmethod
    def _route_query_scope_issue(state: AgentState) -> str:
        """Handle query scope issue routing - go back to database identification for broader perspective."""
        logger.info(
            "Routing to database_identifier due to query_scope_issue (wrong scope/approach)"
        )
        state.current_step = "route_to_database_identifier_scope_issue"
        return "database_identifier"

    @staticmethod
    def _route_sql_issue(state: AgentState, issue_type: str) -> str:
        """Handle SQL generation/planning issue routing."""
        logger.info(f"Routing to query_planner due to {issue_type}")
        state.current_step = f"route_to_query_planner_{issue_type}"
        return "query_planner"

    @staticmethod
    def _route_unknown_issue(state: AgentState, issue_type: str) -> str:
        """Handle unknown issue type routing."""
        logger.warning(
            f"Validation failed ({issue_type or 'unknown'}), retrying from database identification."
        )
        state.current_step = "retry_unknown_issue"
        return "database_identifier"

    @staticmethod
    def _handle_exhausted_retries(state: AgentState) -> None:
        """Handle the case when maximum retries are exhausted."""
        logger.warning(
            "Maximum retries exhausted; ending workflow with best available query."
        )

        feedback = getattr(state, "query_validation_feedback", {}) or {}

        if state.generated_query:
            WorkflowRouter._update_query_with_validation_feedback(
                state.generated_query, feedback
            )
            state.user_message = "Query generated with validation issues after maximum retries. Please review the query and validation feedback carefully."

        state.current_step = "max_retries_exhausted"

    @staticmethod
    def _update_query_with_validation_feedback(query, feedback: dict) -> None:
        """Update query explanation with validation feedback."""
        validation_issues = []
        if feedback.get("issues"):
            validation_issues = [
                issue.get("description", "") for issue in feedback["issues"]
            ]

        suggestions = feedback.get("suggestions", [])

        explanation_parts = []
        if validation_issues:
            explanation_parts.append(f"Issues found: {'; '.join(validation_issues)}")
        if suggestions:
            explanation_parts.append(f"Suggestions: {'; '.join(suggestions)}")

        if explanation_parts:
            combined_explanation = " ".join(explanation_parts)
            query.explanation = f"This query has validation issues but is the best result available: {combined_explanation}"
        else:
            query.explanation = "This query has validation issues but is the best result available after maximum retry attempts."

    @staticmethod
    def decrement_retry_and_log(state: AgentState) -> None:
        """Decrement the global retry counter and log the change."""
        state.retries_left -= 1
        logger.info(f"Retries decremented. Retries left: {state.retries_left}")
