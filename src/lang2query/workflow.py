"""
LangGraph workflow for the Lang2Query system.
This workflow is a hybrid architecture that combines the following agents:
1. Database Identifier Agent - identifies relevant databases for the query
2. Table Identifier Agent - identifies relevant tables from the identified databases
3. Column Identifier Agent - identifies relevant columns from the identified tables
4. Query Planner Agent - creates a logical query plan from the identified columns
5. Query Generator Agent - generates a query from the query plan
6. Query Validator Agent - validates the generated query
"""

import logging
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from lang2query.agents import (
    AgentState,
    ColumnIdentifier,
    DatabaseIdentifierAgent,
    QueryGeneratorAgent,
    QueryPlannerAgent,
    QueryValidatorAgent,
    TableIdentifier,
)
from lang2query.models.wrapper import ModelWrapper
from lang2query.utils import Colors, log_query, log_section_header, log_workflow_step

logger = logging.getLogger(__name__)


class Text2QueryWorkflow:
    """
    Main workflow class implementing the hybrid architecture.

    """

    def __init__(self, model: ModelWrapper, db_connection=None):
        """
        Initialize the workflow with all agents.

        Args:
            model: Generic model wrapper for text generation
            db_connection: Database connection for query execution (optional)
        """
        self.model = model
        self.db_connection = db_connection

        # Initialize all agents
        self.database_identifier = DatabaseIdentifierAgent(model)
        self.table_identifier = TableIdentifier(model)
        self.column_identifier = ColumnIdentifier(model)
        self.query_planner = QueryPlannerAgent(model)
        self.query_generator = QueryGeneratorAgent(model)
        self.query_validator = QueryValidatorAgent(model)

        # Create the workflow graph
        self.workflow = self._create_workflow()
        logger.info("🚀 Lang2Query refined workflow initialized successfully")

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with the refined architecture."""
        workflow = StateGraph(AgentState)

        # Add nodes for each step
        workflow.add_node("database_identifier", self._run_database_identifier)
        workflow.add_node("table_identifier", self._run_table_identifier)
        workflow.add_node("column_identifier", self._run_column_identifier)
        workflow.add_node("query_planner", self._run_query_planner)
        workflow.add_node("query_generator", self._run_query_generator)
        workflow.add_node("query_validator", self._run_query_validator)

        # Define the workflow edges
        workflow.add_edge(START, "database_identifier")
        workflow.add_edge("database_identifier", "table_identifier")
        workflow.add_edge("table_identifier", "column_identifier")
        workflow.add_edge("column_identifier", "query_planner")
        workflow.add_edge("query_planner", "query_generator")
        workflow.add_edge("query_generator", "query_validator")

        # Conditional routing after validation
        workflow.add_conditional_edges(
            "query_validator",
            self._route_after_validation,
            {
                "table_identifier": "table_identifier",
                "query_planner": "query_planner",
                "database_identifier": "database_identifier",
                "end": END,
            },
        )

        return workflow.compile()

    def _run_database_identifier(self, state: AgentState) -> AgentState:
        """Identify relevant databases for the query."""
        log_workflow_step(logger, 1, "Database Identification", "🔍")

        try:
            result = self.database_identifier.process(state)

            if result.success and result.state_updates:
                # Update state with database information
                for key, value in result.state_updates.items():
                    setattr(state, key, value)

                logger.info("✅ Database identification completed successfully")
            else:
                logger.error(f"❌ Database identification failed: {result.message}")
                state.current_step = "database_identification_failed"

            return state

        except Exception as e:
            logger.error(f"❌ Database identification error: {e}")
            state.current_step = "database_identification_error"
            return state

    def _run_table_identifier(self, state: AgentState) -> AgentState:
        """Identify relevant tables from identified databases."""
        log_workflow_step(logger, 2, "Table Identifier", "📊")

        try:
            result = self.table_identifier.process(state)

            if result.success and result.state_updates:
                # Update state with schema information
                for key, value in result.state_updates.items():
                    setattr(state, key, value)

                logger.info("✅ Table identifier completed successfully")
            else:
                logger.error(f"❌ Table identifier failed: {result.message}")
                state.current_step = "table_identifier_failed"

            return state

        except Exception as e:
            logger.error(f"❌ Table identifier error: {e}")
            state.current_step = "table_identifier_error"
            return state

    def _run_column_identifier(self, state: AgentState) -> AgentState:
        """Identify relevant columns from identified tables."""
        log_workflow_step(logger, 3, "Column Identifier", "🧩")
        try:
            result = self.column_identifier.process(state)
            if result.success and result.state_updates:
                for key, value in result.state_updates.items():
                    setattr(state, key, value)
                logger.info("✅ Column identifier completed successfully")
            else:
                logger.error(f"❌ Column identifier failed: {result.message}")
                state.current_step = "column_identifier_failed"
            return state
        except Exception as e:
            logger.error(f"❌ Column identifier error: {e}")
            state.current_step = "column_identifier_error"
            return state

    def _run_query_planner(self, state: AgentState) -> AgentState:
        """Create logical query plan from question and schema."""
        log_workflow_step(logger, 4, "Query Planning", "🧠")

        try:
            result = self.query_planner.process(state)

            if result.success and result.state_updates:
                # Update state with query plan
                for key, value in result.state_updates.items():
                    setattr(state, key, value)

                logger.info("✅ Query planning completed successfully")
            else:
                logger.error(f"❌ Query planning failed: {result.message}")
                state.current_step = "query_planning_failed"

            return state

        except Exception as e:
            logger.error(f"❌ Query planning error: {e}")
            state.current_step = "query_planning_error"
            return state

    def _run_query_generator(self, state: AgentState) -> AgentState:
        """Generate Query from query plan and schema."""
        log_workflow_step(logger, 5, "Query Generation", "🔨")

        try:
            result = self.query_generator.process(state)

            if result.success and result.state_updates:
                for key, value in result.state_updates.items():
                    setattr(state, key, value)

                logger.info("✅ Query generation completed")
                if state.generated_query:
                    logger.info(
                        f"📝 Generated query: {state.generated_query.query[:100]}..."
                    )
            else:
                logger.error(f"❌ Query generation failed: {result.message}")
                state.current_step = "query_generation_failed"

            return state

        except Exception as e:
            logger.error(f"❌ Query generation error: {e}")
            state.current_step = "query_generation_error"
            return state

    def _run_query_validator(self, state: AgentState) -> AgentState:
        """Validate the generated query."""
        log_workflow_step(logger, 6, "Query Validation", "🔍")

        try:
            result = self.query_validator.process(state)

            if result.success and result.state_updates:
                # Update state with validation results
                for key, value in result.state_updates.items():
                    setattr(state, key, value)

                logger.info("✅ Query validation completed successfully")
            else:
                logger.error(f"❌ Query validation failed: {result.message}")
                state.current_step = "query_validation_failed"

            return state

        except Exception as e:
            logger.error(f"❌ Query validation error: {e}")
            state.current_step = "query_validation_error"
            return state

    def _route_after_validation(self, state: AgentState) -> str:
        """Router to decide next step after query validation with diagnostics.

        Rules:
        - If valid: end.
        - If feedback indicates missing table/column/schema: route to table_identifier.
        - If SQL generation issue but schema sufficient: route to query_planner.
        - If insufficient data and no retries left: inform user and end.
        - Otherwise and retries remain: decrement and restart from database_identifier to rebuild context.
        """
        # If valid, end workflow
        if getattr(state, "is_query_valid", False):
            state.current_step = "workflow_completed"
            return "end"

        feedback = getattr(state, "query_validation_feedback", {}) or {}
        issue_type = feedback.get("issue_type") or state.last_error_type

        # Insufficient data: short-circuit if we've already tried
        if issue_type == "insufficient_data":
            if state.retries_left <= 0:
                msg = "Insufficient data to fulfill the request after multiple attempts. Please provide more specifics (e.g., relevant tables, columns, or filters)."
                logger.warning(f"⚠️ {msg}")
                state.user_message = msg
                state.current_step = "insufficient_data_exit"
                return "end"
            # else: try to rebuild from the beginning once
            logger.warning(
                "⚠️ Insufficient data detected; attempting broader re-identification."
            )
            state.retries_left -= 1
            state.current_step = "retry_due_to_insufficient_data"
            return "database_identifier"

        # Missing schema elements → go back to table identification
        if issue_type == "schema_missing":
            logger.info(
                "🔄 Routing to table_identifier due to schema issues (missing tables/columns)"
            )
            state.current_step = "route_to_table_identifier"
            return "table_identifier"

        # SQL generation/planning issue → go to planner to refine plan
        if issue_type == "sql_generation_issue":
            logger.info("🔄 Routing to query_planner due to SQL generation issues")
            state.current_step = "route_to_query_planner"
            return "query_planner"

        # Unknown but retries remain → restart earlier in the pipeline
        if state.retries_left > 0:
            logger.warning(
                f"⚠️ Validation failed (unknown type), retrying from database identification. Retries left before decrement: {state.retries_left}"
            )
            state.retries_left -= 1
            state.current_step = "retry_unknown_issue"
            return "database_identifier"

        # No retries left → end
        logger.warning("⚠️ No retries left; ending workflow.")
        state.current_step = "workflow_completed"
        return "end"

    def process_query(self, natural_language_query: str) -> AgentState:
        """
        Process a natural language query through the refined workflow.

        Args:
            natural_language_query: The natural language query to process

        Returns:
            Final state with all processing results
        """
        log_section_header(
            logger,
            f"🚀 PROCESSING QUERY: {natural_language_query[:50]}{'...' if len(natural_language_query) > 50 else ''}",
        )
        logger.info(
            f"{Colors.BRIGHT_CYAN}📝 Full Query: {natural_language_query}{Colors.RESET}"
        )

        # Create initial state
        initial_state = AgentState(
            natural_language_query=natural_language_query,
            current_step="workflow_started",
            retries_left=3,
        )

        try:
            # Run the workflow with recursion limit to prevent infinite loops
            final_state = self.workflow.invoke(
                initial_state, config={"recursion_limit": 20}
            )

            # Handle potential dict return (LangGraph sometimes returns dict)
            if isinstance(final_state, dict):
                logger.debug("Converting dict response to AgentState")
                final_state = AgentState(**final_state)

            # Log final results
            self._log_final_results(final_state)

            return final_state

        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            initial_state.current_step = "workflow_failed"
            return initial_state

    def _log_final_results(self, state: AgentState) -> None:
        """Log comprehensive final results."""
        logger.info("=" * 80)
        logger.info("📋 WORKFLOW COMPLETION SUMMARY")
        logger.info("=" * 80)

        logger.info(f"🎯 Final Status: {state.current_step}")
        logger.info(f"🔄 Retries Left: {state.retries_left}")
        logger.info(f"📊 Confidence Score: {state.confidence_score:.2f}")

        if state.relevant_databases:
            logger.info(
                f"🗄️ Identified Databases: {', '.join(state.relevant_databases)}"
            )
            logger.info(f"✅ DB Retrieved Flag: {state.db_retrieved}")

        if state.relevant_tables:
            logger.info(
                f"📚 Tables Retrieved: {len(state.relevant_tables)} tables | Flag: {state.tables_retrieved}"
            )

        if state.relevant_columns:
            logger.info(
                f"🧩 Columns Retrieved: {len(state.relevant_columns)} columns | Flag: {state.columns_retrieved}"
            )

        if state.query_plan:
            logger.info(f"🧠 Query Plan: {state.query_plan[:100]}...")

        if state.generated_query:
            log_query(
                logger,
                state.generated_query.query,
                state.generated_query.confidence_score,
            )

        if state.query_validation_feedback:
            feedback = state.query_validation_feedback
            validation_status = (
                "✅ VALID" if feedback.get("overall_valid", False) else "❌ INVALID"
            )
            logger.info(f"🔍 Query Validation: {validation_status}")
            if not feedback.get("overall_valid", True):
                logger.info(f"📝 Issues found: {feedback.get('total_issues', 0)}")
                logger.info(f"💡 Suggestions: {len(feedback.get('suggestions', []))}")
                issue_type = feedback.get("issue_type")
                if issue_type:
                    logger.info(f"🧭 Classified Issue Type: {issue_type}")

        if getattr(state, "user_message", None):
            logger.info(f"📣 User Notice: {state.user_message}")

        logger.info("=" * 80)

    def get_workflow_summary(self, state: AgentState) -> Dict[str, Any]:
        """Get a comprehensive summary of the workflow execution."""
        return {
            "natural_language_query": state.natural_language_query,
            "status": state.current_step,
            "retries_left": state.retries_left,
            "confidence_score": state.confidence_score,
            "databases": {
                "identified": state.relevant_databases,
                "count": len(state.relevant_databases),
                "retrieved": state.db_retrieved,
            },
            "tables": {
                "retrieved": state.tables_retrieved,
                "count": len(state.relevant_tables) if state.relevant_tables else 0,
                "preview": ", ".join(state.relevant_tables[:5])
                + (
                    "..."
                    if state.relevant_tables and len(state.relevant_tables) > 5
                    else ""
                ),
            },
            "columns": {
                "retrieved": state.columns_retrieved,
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
                "preview": (
                    state.query_plan[:100] + "..."
                    if state.query_plan and len(state.query_plan) > 100
                    else state.query_plan
                ),
            },
            "query": {
                "query": state.generated_query.query if state.generated_query else None,
                "confidence": (
                    state.generated_query.confidence_score
                    if state.generated_query
                    else 0.0
                ),
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
        }
