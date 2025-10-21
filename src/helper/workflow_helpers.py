"""
Helper functions and utilities for the Text2Query workflow.
Contains logging, routing, and state management utilities.
"""

import logging
from models.models import AgentState

logger = logging.getLogger(__name__)


class WorkflowLogger:
    """Centralized logging utilities for workflow steps and results."""

    @staticmethod
    def log_database_results(state: AgentState) -> None:
        """Log database identification results."""
        if hasattr(state, 'relevant_databases') and state.relevant_databases:
            logger.info(f"🗄️ Databases identified: {', '.join(state.relevant_databases)}")

    @staticmethod
    def log_table_results(state: AgentState) -> None:
        """Log table identification results."""
        if hasattr(state, 'relevant_tables') and state.relevant_tables:
            tables_preview = ', '.join(state.relevant_tables[:3])
            if len(state.relevant_tables) > 3:
                tables_preview += f" (+{len(state.relevant_tables) - 3} more)"
            logger.info(f"📋 Tables identified: {tables_preview}")

    @staticmethod
    def log_column_results(state: AgentState) -> None:
        """Log column identification results."""
        if hasattr(state, 'relevant_columns') and state.relevant_columns:
            columns_preview = ', '.join(state.relevant_columns[:3])
            if len(state.relevant_columns) > 3:
                columns_preview += f" (+{len(state.relevant_columns) - 3} more)"
            logger.info(f"🔍 Columns identified: {columns_preview}")

    @staticmethod
    def log_schema_results(state: AgentState) -> None:
        """Log schema building results."""
        if hasattr(state, 'schema_context') and state.schema_context:
            logger.info(f"🏗️ Schema context built with {len(str(state.schema_context))} characters")

    @staticmethod
    def log_planning_results(state: AgentState) -> None:
        """Log query planning results."""
        if hasattr(state, 'query_plan') and state.query_plan:
            plan_preview = str(state.query_plan)[:100] + "..." if len(str(state.query_plan)) > 100 else str(state.query_plan)
            logger.info(f"🧠 Query plan created: {plan_preview}")

    @staticmethod
    def log_validation_results(state: AgentState) -> None:
        """Log query validation results."""
        if hasattr(state, 'is_query_valid'):
            status = "✅ Valid" if state.is_query_valid else "❌ Invalid"
            logger.info(f"🔍 Query validation: {status}")

    @staticmethod
    def log_agent_results(step_name: str, state: AgentState) -> None:
        """Log specific results from each agent for live display."""
        step_type = step_name.lower().replace(' ', '_')
        log_method_map = {
            'database_identification': WorkflowLogger.log_database_results,
            'table_identifier': WorkflowLogger.log_table_results,
            'column_identifier': WorkflowLogger.log_column_results,
            'schema_builder': WorkflowLogger.log_schema_results,
            'query_planning': WorkflowLogger.log_planning_results,
            'query_validation': WorkflowLogger.log_validation_results,
        }

        if step_type in log_method_map:
            log_method_map[step_type](state)


class WorkflowRouter:
    """Centralized routing logic for workflow state transitions."""

    @staticmethod
    def check_permanent_failure(state: AgentState, step_context: str = "", return_failed_step: bool = False) -> str:
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

        current_step = getattr(state, 'current_step', '')
        if current_step.endswith('_failed') or current_step.endswith('_error'):
            context_msg = f" {step_context}" if step_context else ""
            logger.error(f"❌{context_msg} failed permanently")

            if return_failed_step:
                step_name = current_step.replace('_failed', '').replace('_error', '')
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
            logger.info(f"🔄 Resuming: Routing directly to {resume_node}")
            return resume_node

        if getattr(state, "is_metadata_query", False):
            logger.info("🔄 Routing to metadata agent for metadata query")
            return "metadata_agent"
        else:
            logger.info("🔄 Routing to database identifier for data query")
            return "database_identifier"

    @staticmethod
    def route_after_database_identifier(state: AgentState) -> str:
        """Route after database identifier based on interaction mode and retry status."""
        # Check if step failed permanently
        failure_result = WorkflowRouter.check_permanent_failure(state, "Database identifier")
        if failure_result:
            return failure_result

        # Check if this step needs to be retried (only for actual step failures, not resumes)
        if getattr(state, 'last_error_type', None) == "step_retry" and not getattr(state, 'is_resuming', False):
            logger.info("🔄 Retrying database identifier step")
            return "database_identifier"

        # Normal routing based on interaction mode
        mode = getattr(state, "interaction_mode", "ask")
        if mode == "interactive":
            logger.info("🔄 Interactive mode: Routing to database human review")
            return "database_human_review"
        else:
            logger.info("🔄 Ask mode: Skipping human review, proceeding to table identifier")
            return "table_identifier"

    @staticmethod
    def route_after_database_human_feedback(state: AgentState) -> str:
        """Route after database human feedback based on approval status and modification type."""
        approvals = getattr(state, 'human_approvals', {}) or {}
        approved = approvals.get('databases', False)
        
        if approved:
            logger.info("✅ User approved databases, proceeding to table identifier")
            return "table_identifier"
        
        # Check if we need to show updated list (modifications made) or re-identify
        modification_type = getattr(state, 'last_modification_type', None)
        feedback_processed = getattr(state, 'feedback_processed', False)
        
        if feedback_processed and modification_type in ['add', 'remove', 'modify']:
            logger.info("🔄 Modifications applied, showing updated database list to user")
            # Clear the flag so next iteration doesn't loop
            state.feedback_processed = False
            return "database_human_review"
        else:
            logger.info("🔄 User rejected databases, re-running database identification")
            return "database_identifier"

    @staticmethod
    def route_after_table_identifier(state: AgentState) -> str:
        """Route after table identifier based on interaction mode and retry status."""
        # Check if step failed permanently
        failure_result = WorkflowRouter.check_permanent_failure(state, "Table identifier")
        if failure_result:
            return failure_result

        # Check if this step needs to be retried (only for actual step failures, not resumes)
        if getattr(state, 'last_error_type', None) == "step_retry" and not getattr(state, 'is_resuming', False):
            logger.info("🔄 Retrying table identifier step")
            return "table_identifier"

        # Normal routing based on interaction mode
        mode = getattr(state, "interaction_mode", "ask")
        if mode == "interactive":
            logger.info("🔄 Interactive mode: Routing to table human review")
            return "table_human_review"
        else:
            logger.info("🔄 Ask mode: Skipping human review, proceeding to column identifier")
            return "column_identifier"

    @staticmethod
    def route_after_table_human_feedback(state: AgentState) -> str:
        """Route after table human feedback based on approval status and modification type."""
        approvals = getattr(state, 'human_approvals', {}) or {}
        approved = approvals.get('tables', False)
        
        if approved:
            logger.info("✅ User approved tables, proceeding to column identifier")
            return "column_identifier"
        
        # Check if we need to show updated list (modifications made) or re-identify
        modification_type = getattr(state, 'last_modification_type', None)
        feedback_processed = getattr(state, 'feedback_processed', False)
        
        if feedback_processed and modification_type in ['add', 'remove', 'modify']:
            logger.info("🔄 Modifications applied, showing updated table list to user")
            # Clear the flag so next iteration doesn't loop
            state.feedback_processed = False
            return "table_human_review"
        else:
            logger.info("🔄 User rejected tables, re-running table identification")
            return "table_identifier"

    @staticmethod
    def route_after_pipeline_step(state: AgentState) -> str:
        """Route after a pipeline step (column_identifier, schema_builder, etc.) checking for retries."""
        from langgraph.graph import END

        # Check if this step needs to be retried
        if getattr(state, 'last_error_type', None) == "step_retry":
            current_step = getattr(state, 'current_step', '')
            if current_step.endswith('_retry'):
                step_name = current_step.replace('_retry', '')
                logger.info(f"🔄 Retrying pipeline step: {step_name}")
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
        if getattr(state, 'last_error_type', None) == "step_retry":
            logger.info("🔄 Retrying metadata agent step")
            return "metadata_agent"

        # Check if step failed permanently
        failure_result = WorkflowRouter.check_permanent_failure(state, "Metadata agent")
        if failure_result:
            return failure_result

        # Metadata queries end the workflow
        logger.info("✅ Metadata query completed")
        return END

    @staticmethod
    def _get_next_step_from_current(state: AgentState) -> str:
        """Get the next step based on current step completion."""
        from langgraph.graph import END

        current_step = getattr(state, 'current_step', '')

        # Map completion steps to next steps
        next_step_map = {
            "column_identification_completed": "schema_builder",
            "schema_building_completed": "query_planner",
            "query_planning_completed": "query_generator",
            "query_generation_completed": "query_validator",
        }

        for completion_step, next_step in next_step_map.items():
            if completion_step in current_step:
                return next_step

        # Default fallback
        return END


class StateManager:
    """Utilities for managing agent state updates."""

    @staticmethod
    def update_state_with_preservation(state: AgentState, updates: dict) -> None:
        """Update state while preserving critical system fields."""
        system_fields_to_preserve = ['retries_left', 'is_query_valid']

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


class AgentRunner:
    """Helper class for running agents with standardized patterns."""

    @staticmethod
    def create_agent_config(
        step_number: int,
        step_name: str,
        step_emoji: str,
        success_step: str,
        error_step: str
    ) -> dict:
        """Create configuration for agent execution."""
        return {
            'step_number': step_number,
            'step_name': step_name,
            'step_emoji': step_emoji,
            'success_step': success_step,
            'error_step': error_step
        }
