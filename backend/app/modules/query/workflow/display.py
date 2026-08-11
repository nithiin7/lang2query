"""Logging and user-facing display utilities for the Text2Query workflow."""

import logging
from typing import Any, Dict

from models import AgentState

logger = logging.getLogger(__name__)


class WorkflowLogger:
    """Centralized logging utilities for workflow steps and results."""

    @staticmethod
    def log_database_results(state: AgentState) -> None:
        """Log database identification results."""
        if hasattr(state, "relevant_databases") and state.relevant_databases:
            logger.info(f"Databases identified: {', '.join(state.relevant_databases)}")

    @staticmethod
    def log_table_results(state: AgentState) -> None:
        """Log table identification results."""
        if hasattr(state, "relevant_tables") and state.relevant_tables:
            tables_preview = ", ".join(state.relevant_tables[:3])
            if len(state.relevant_tables) > 3:
                tables_preview += f" (+{len(state.relevant_tables) - 3} more)"
            logger.info(f"Tables identified: {tables_preview}")

    @staticmethod
    def log_column_results(state: AgentState) -> None:
        """Log column identification results."""
        if hasattr(state, "relevant_columns") and state.relevant_columns:
            columns_preview = ", ".join(state.relevant_columns[:3])
            if len(state.relevant_columns) > 3:
                columns_preview += f" (+{len(state.relevant_columns) - 3} more)"
            logger.info(f"Columns identified: {columns_preview}")

    @staticmethod
    def log_schema_results(state: AgentState) -> None:
        """Log schema building results."""
        if hasattr(state, "schema_context") and state.schema_context:
            logger.info(
                f"Schema context built with {len(str(state.schema_context))} characters"
            )

    @staticmethod
    def log_planning_results(state: AgentState) -> None:
        """Log query planning results."""
        if hasattr(state, "query_plan") and state.query_plan:
            plan_preview = (
                str(state.query_plan)[:100] + "..."
                if len(str(state.query_plan)) > 100
                else str(state.query_plan)
            )
            logger.info(f"Query plan created: {plan_preview}")

    @staticmethod
    def log_validation_results(state: AgentState) -> None:
        """Log query validation results."""
        if hasattr(state, "is_query_valid"):
            status = "Valid" if state.is_query_valid else "Invalid"
            logger.info(f"Query validation: {status}")

    @staticmethod
    def log_agent_results(step_name: str, state: AgentState) -> None:
        """Log specific results from each agent for live display."""
        step_type = step_name.lower().replace(" ", "_")
        log_method_map = {
            "database_identification": WorkflowLogger.log_database_results,
            "table_identifier": WorkflowLogger.log_table_results,
            "column_identifier": WorkflowLogger.log_column_results,
            "schema_builder": WorkflowLogger.log_schema_results,
            "query_planning": WorkflowLogger.log_planning_results,
            "query_validation": WorkflowLogger.log_validation_results,
        }

        if step_type in log_method_map:
            log_method_map[step_type](state)


STEP_DISPLAY_MAP = {
    "workflow_started": "Starting workflow...",
    "processing_routing": "Analyzing query type...",
    "routing_completed": "Query type identified",
    "processing_metadata_agent": "Processing metadata query...",
    "processing_database_identification": "Identifying relevant databases...",
    "processing_database_review": "Reviewing database selection...",
    "processing_table_identifier": "Finding relevant tables...",
    "processing_table_review": "Reviewing table selection...",
    "processing_column_identifier": "Discovering relevant columns...",
    "processing_schema_builder": "Building schema context...",
    "processing_query_planning": "Creating query plan...",
    "processing_query_generation": "Generating SQL query...",
    "processing_sql_safety_guard": "Checking query is read-only...",
    "sql_safety_check_failed": "Query rejected: not read-only",
    "processing_query_validation": "Validating generated query...",
    "metadata_completed": "Metadata query completed",
    "database_review_completed": "Database review completed",
    "table_review_completed": "Table review completed",
    "workflow_completed": "Workflow completed successfully",
    "max_retries_exhausted": "Maximum retries reached",
    "workflow_failed": "Workflow failed",
}


class WorkflowDisplay:
    """User-facing presentation helpers built from AgentState (no graph logic)."""

    @staticmethod
    def get_current_step_display(state: AgentState) -> str:
        """Get user-friendly display text for current step."""
        return STEP_DISPLAY_MAP.get(
            state.current_step, f"{state.current_step.replace('_', ' ').title()}..."
        )

    @staticmethod
    def get_workflow_summary(state: AgentState) -> Dict[str, Any]:
        """Get a comprehensive summary of the workflow execution."""
        return {
            "natural_language_query": state.natural_language_query,
            "status": state.current_step,
            "current_step_display": WorkflowDisplay.get_current_step_display(state),
            "retries_left": state.retries_left,
            "databases": {
                "identified": state.relevant_databases,
                "count": len(state.relevant_databases),
            },
            "tables": {
                "retrieved": (
                    len(state.relevant_tables) > 0 if state.relevant_tables else False
                ),
                "count": len(state.relevant_tables) if state.relevant_tables else 0,
                "preview": ", ".join(state.relevant_tables[:5])
                + (
                    "..."
                    if state.relevant_tables and len(state.relevant_tables) > 5
                    else ""
                ),
            },
            "columns": {
                "retrieved": (
                    len(state.relevant_columns) > 0 if state.relevant_columns else False
                ),
                "count": len(state.relevant_columns) if state.relevant_columns else 0,
                "preview": ", ".join(state.relevant_columns[:5])
                + (
                    "..."
                    if state.relevant_columns and len(state.relevant_columns) > 5
                    else ""
                ),
            },
            "query_plan": {
                "created": bool(state.query_plan),
                "count": len(state.query_plan) if state.query_plan else 0,
                "preview": state.query_plan,
            },
            "query": {
                "query": state.generated_query.query if state.generated_query else None,
                "explanation": (
                    state.generated_query.explanation if state.generated_query else None
                ),
            },
            "validation": {
                "is_valid": state.is_query_valid,
                "issues_count": (
                    state.query_validation_feedback.get("total_issues", 0)
                    if state.query_validation_feedback
                    else 0
                ),
                "suggestions_count": (
                    len(state.query_validation_feedback.get("suggestions", []))
                    if state.query_validation_feedback
                    else 0
                ),
                "overall_valid": (
                    state.query_validation_feedback.get("overall_valid", False)
                    if state.query_validation_feedback
                    else False
                ),
            },
            "metadata_response": state.metadata_response,
        }
