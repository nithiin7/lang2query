"""
LangGraph workflow for the text2query system.

This workflow implements a hybrid agent architecture that combines multiple specialized agents:
0. Router Agent - routes the query to the appropriate agent
1. Database Identifier Agent - identifies relevant databases for the query
2. Table Identifier Agent - identifies relevant tables from the identified databases
3. Column Identifier Agent - identifies relevant columns from the identified tables
4. Schema Builder Agent - builds comprehensive schema context from identified components
5. Query Planner Agent - creates a logical query plan from the schema context
6. Query Generator Agent - generates a query from the query plan
7. Query Validator Agent - validates the generated query
"""

import logging
import uuid
from typing import Dict, Any, Iterator, Optional, Union

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents import (
    RouterAgent,
    MetadataAgent,
    DatabaseIdentifierAgent,
    TableIdentifier,
    ColumnIdentifier,
    SchemaBuilderAgent,
    QueryPlannerAgent,
    QueryGeneratorAgent,
    QueryValidatorAgent,
    AgentState,
    HumanInTheLoopAgent
)
from config import KB_DIRECTORY, COLLECTION_NAME, EMBEDDING_MODEL_PATH
from lib import ModelWrapper
from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever
from utils import log_section_header, log_workflow_step, Colors
from helper.workflow_helpers import WorkflowLogger, WorkflowRouter, StateManager

logger = logging.getLogger(__name__)


class Text2QueryWorkflow:
    """Main workflow class implementing the hybrid agent architecture."""
    
    def __init__(self, model: ModelWrapper, docs_dir: str = "docs"):
        """
        Initialize the workflow with all agents.
        
        Args:
            model: Generic model wrapper for text generation
            docs_dir: Directory containing database metadata JSON files (default: "docs")
        """
        self.model = model
        self.docs_dir = docs_dir

        # Initialize shared retriever instance
        self.retriever = None
        try:
            self.retriever = SQLKnowledgeBaseRetriever(
                model_path=EMBEDDING_MODEL_PATH,
                chroma_persist_dir=str(KB_DIRECTORY),
                collection_name=COLLECTION_NAME
            )
            logger.info("✅ Shared retriever initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  Shared retriever initialization failed: {e}")

        # Initialize all agents
        self.router = RouterAgent(model)
        self.metadata_agent = MetadataAgent(model, retriever=self.retriever)
        self.database_identifier = DatabaseIdentifierAgent(model, retriever=self.retriever)
        self.database_human_review = HumanInTheLoopAgent(
            model,
            confirmation_type="databases",
            data_source="relevant_databases",
            retriever=self.retriever
        )
        self.table_human_review = HumanInTheLoopAgent(
            model,
            confirmation_type="tables",
            data_source="relevant_tables",
            retriever=self.retriever
        )
        self.table_identifier = TableIdentifier(model, retriever=self.retriever)
        self.column_identifier = ColumnIdentifier(model, retriever=self.retriever)
        self.schema_builder = SchemaBuilderAgent(model, retriever=self.retriever)
        self.query_planner = QueryPlannerAgent(model, retriever=self.retriever)
        self.query_generator = QueryGeneratorAgent(model, retriever=self.retriever)
        self.query_validator = QueryValidatorAgent(model, retriever=self.retriever)
        
        # Create the workflow graph
        self.checkpointer = MemorySaver()
        self.workflow = self._create_workflow()
        logger.info("🚀 Text2Query workflow initialized successfully")

    def process_query(
        self,
        natural_language_query: str,
        interaction_mode: str = "ask",
        streaming: bool = False,
        callback: Optional[callable] = None,
    ) -> Union[AgentState, Iterator[AgentState]]:
        """
        Process a natural language query through the refined workflow.

        Args:
            natural_language_query: The natural language query to process
            interaction_mode: "interactive" for human-in-the-loop, "ask" for automatic processing
            streaming: If True, yields state updates as they happen
            callback: Optional callback invoked on each streamed update (node_name, state)

        Returns:
            - If streaming is False: the final AgentState
            - If streaming is True: an iterator yielding AgentState updates
        """
        if streaming:
            return self._process_query_stream(natural_language_query, interaction_mode, callback)

        log_section_header(logger, f"🚀 PROCESSING QUERY: {natural_language_query[:50]}{'...' if len(natural_language_query) > 50 else ''}")
        logger.info(f"{Colors.BRIGHT_CYAN}📝 Full Query: {natural_language_query}{Colors.RESET}")
        logger.info(f"🎯 Interaction Mode: {interaction_mode}")

        # Create initial state
        initial_state = AgentState(
            natural_language_query=natural_language_query,
            interaction_mode=interaction_mode,
            current_step="workflow_started",
            retries_left=3
        )

        try:
            # Generate a unique thread ID for this workflow execution
            thread_id = str(uuid.uuid4())
            logger.debug(f"Using thread ID: {thread_id}")

            # Run the workflow with recursion limit to prevent infinite loops
            final_state = self.workflow.invoke(
                initial_state,
                config={
                    "recursion_limit": 20,
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            )

            # Handle potential dict return (LangGraph sometimes returns dict)
            if isinstance(final_state, dict):
                logger.debug("Converting dict response to AgentState")
                final_state = AgentState(**final_state)

            return final_state

        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            initial_state.current_step = "workflow_failed"
            return initial_state

    def resume_from_state(self, state: AgentState, callback: Optional[callable] = None):
        """
        Resume the workflow from a provided state, yielding streaming updates.

        Note: This uses the original workflow but modifies routing to start from
        the appropriate node based on the current state.
        """
        try:
            thread_id = str(uuid.uuid4())
            logger.debug(f"Resuming workflow with new thread ID: {thread_id}")

            # Determine the appropriate starting node based on current state
            start_node = self._determine_resume_node(state)
            logger.info(f"🔄 Resuming workflow from node: {start_node}")

            # Mark state as resuming to modify routing behavior
            state.is_resuming = True
            state.resume_start_node = start_node

            # Use the original workflow - router will route directly to start_node
            for chunk in self.workflow.stream(
                state,
                config={
                    "recursion_limit": 20,
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            ):
                if isinstance(chunk, dict) and len(chunk) == 1:
                    node_name = list(chunk.keys())[0]
                    new_state = chunk[node_name]

                    if isinstance(new_state, dict):
                        new_state = AgentState(**new_state)

                    if callback:
                        callback(node_name, new_state)

                    yield new_state

                    step_display = self.get_current_step_display(new_state)
                    logger.info(f"📊 Resume update from {node_name}: {step_display}")

        except Exception as e:
            logger.error(f"❌ Workflow resume failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            state.current_step = "workflow_failed"
            yield state

    def get_current_step_display(self, state: AgentState) -> str:
        """Get user-friendly display text for current step."""
        step_mapping = {
            "workflow_started": "🚀 Starting workflow...",
            "processing_routing": "🧭 Analyzing query type...",
            "routing_completed": "✅ Query type identified",
            "processing_metadata_agent": "📊 Processing metadata query...",
            "processing_database_identification": "🗄️ Identifying relevant databases...",
            "processing_database_review": "👤 Reviewing database selection...",
            "processing_table_identifier": "📋 Finding relevant tables...",
            "processing_table_review": "👤 Reviewing table selection...",
            "processing_column_identifier": "🔍 Discovering relevant columns...",
            "processing_schema_builder": "🏗️ Building schema context...",
            "processing_query_planning": "🧠 Creating query plan...",
            "processing_query_generation": "⚡ Generating SQL query...",
            "processing_query_validation": "✅ Validating generated query...",
            "metadata_completed": "✅ Metadata query completed",
            "database_review_completed": "✅ Database review completed",
            "table_review_completed": "✅ Table review completed",
            "workflow_completed": "🎉 Workflow completed successfully",
            "max_retries_exhausted": "⚠️ Maximum retries reached",
            "workflow_failed": "❌ Workflow failed"
        }

        return step_mapping.get(state.current_step, f"🔄 {state.current_step.replace('_', ' ').title()}...")

    def get_workflow_summary(self, state: AgentState) -> Dict[str, Any]:
        """Get a comprehensive summary of the workflow execution."""
        return {
            "natural_language_query": state.natural_language_query,
            "status": state.current_step,
            "current_step_display": self.get_current_step_display(state),
            "retries_left": state.retries_left,
            "databases": {
                "identified": state.relevant_databases,
                "count": len(state.relevant_databases),
            },
            "tables": {
                "retrieved": len(state.relevant_tables) > 0 if state.relevant_tables else False,
                "count": len(state.relevant_tables) if state.relevant_tables else 0,
                "preview": ', '.join(state.relevant_tables[:5]) + ("..." if state.relevant_tables and len(state.relevant_tables) > 5 else "")
            },
            "columns": {
                "retrieved": len(state.relevant_columns) > 0 if state.relevant_columns else False,
                "count": len(state.relevant_columns) if state.relevant_columns else 0,
                "preview": ', '.join(state.relevant_columns[:5]) + ("..." if state.relevant_columns and len(state.relevant_columns) > 5 else "")
            },
            "query_plan": {
                "created": bool(state.query_plan),
                "count": len(state.query_plan) if state.query_plan else 0,
                "preview": state.query_plan
            },
            "query": {
                "query": state.generated_query.query if state.generated_query else None,
                "explanation": state.generated_query.explanation if state.generated_query else None
            },
            "validation": {
                "is_valid": state.is_query_valid,
                "issues_count": state.query_validation_feedback.get('total_issues', 0) if state.query_validation_feedback else 0,
                "suggestions_count": len(state.query_validation_feedback.get('suggestions', [])) if state.query_validation_feedback else 0,
                "overall_valid": state.query_validation_feedback.get('overall_valid', False) if state.query_validation_feedback else False
            },
            "metadata_response": state.metadata_response,
        }


    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with the refined architecture."""
        workflow = StateGraph(AgentState)

        # Define agent nodes with their handlers
        agents = [
            ("router", self._run_router),
            ("metadata_agent", self._run_metadata_agent),
            ("database_identifier", self._run_database_identifier),
            ("database_human_review", self._run_database_human_review),
            ("table_identifier", self._run_table_identifier),
            ("table_human_review", self._run_table_human_review),
            ("column_identifier", self._run_column_identifier),
            ("schema_builder", self._run_schema_builder),
            ("query_planner", self._run_query_planner),
            ("query_generator", self._run_query_generator),
            ("query_validator", self._run_query_validator),
        ]

        # Add all agent nodes
        for node_name, handler in agents:
            workflow.add_node(node_name, handler)

        # Define workflow flow
        workflow.add_edge(START, "router")

        # Router branching
        router_targets = {
            "metadata_agent": "metadata_agent",
            "database_identifier": "database_identifier",
            "database_human_review": "database_human_review",
            "table_identifier": "table_identifier",
            "table_human_review": "table_human_review",
            "column_identifier": "column_identifier",
            "schema_builder": "schema_builder",
            "query_planner": "query_planner",
            "query_generator": "query_generator",
            "query_validator": "query_validator",
            "end": END
        }

        workflow.add_conditional_edges(
            "router",
            self._route_after_router,
            router_targets
        )

        # Metadata flow
        workflow.add_edge("metadata_agent", END)

        # Conditional routing after database_identifier based on interaction mode
        workflow.add_conditional_edges(
            "database_identifier",
            self._route_after_database_identifier,
            {
                "database_human_review": "database_human_review",
                "table_identifier": "table_identifier"
            }
        )

        # Conditional routing after database human review
        workflow.add_conditional_edges(
            "database_human_review",
            self._route_after_database_human_feedback,
            {
                "database_human_review": "database_human_review",  # Show updated list after modifications
                "database_identifier": "database_identifier",  # Re-identify if rejected
                "table_identifier": "table_identifier"  # Proceed if approved
            }
        )

        # Conditional routing after table_identifier based on interaction mode
        workflow.add_conditional_edges(
            "table_identifier",
            self._route_after_table_identifier,
            {
                "table_human_review": "table_human_review",
                "column_identifier": "column_identifier"
            }
        )

        # Conditional routing after table human review
        workflow.add_conditional_edges(
            "table_human_review",
            self._route_after_table_human_feedback,
            {
                "table_human_review": "table_human_review",  # Show updated list after modifications
                "table_identifier": "table_identifier",  # Re-identify if rejected
                "column_identifier": "column_identifier"  # Proceed if approved
            }
        )

        # Add conditional edges for the main processing pipeline to handle retries
        workflow.add_conditional_edges(
            "column_identifier",
            self._route_after_pipeline_step,
            {
                "column_identifier": "column_identifier",  # Retry
                "schema_builder": "schema_builder",  # Continue
                END: END,  # Fail
            }
        )

        workflow.add_conditional_edges(
            "schema_builder",
            self._route_after_pipeline_step,
            {
                "schema_builder": "schema_builder",  # Retry
                "query_planner": "query_planner",  # Continue
                END: END,  # Fail
            }
        )

        workflow.add_conditional_edges(
            "query_planner",
            self._route_after_pipeline_step,
            {
                "query_planner": "query_planner",  # Retry
                "query_generator": "query_generator",  # Continue
                END: END,  # Fail
            }
        )

        workflow.add_conditional_edges(
            "query_generator",
            self._route_after_pipeline_step,
            {
                "query_generator": "query_generator",  # Retry
                "query_validator": "query_validator",  # Continue
                END: END,  # Fail
            }
        )

        # Metadata agent routing
        workflow.add_conditional_edges(
            "metadata_agent",
            self._route_after_metadata_step,
            {
                "metadata_agent": "metadata_agent",  # Retry
                END: END,  # Continue or fail
            }
        )

        # Validation retry logic
        workflow.add_conditional_edges(
            "query_validator",
            self._route_after_validation,
            {
                "database_identifier": "database_identifier",
                "table_identifier": "table_identifier",
                "query_planner": "query_planner",
                "end": END,
            }
        )

        return workflow.compile(checkpointer=self.checkpointer)


    def _run_agent(self, state: AgentState, agent, step_number: int, step_name: str,
                   step_emoji: str, success_step: str, error_step: str) -> AgentState:
        """Common method to run any agent with standardized error handling and logging."""
        log_workflow_step(logger, step_number, step_name, step_emoji)

        # Update current step for real-time display
        state.current_step = f"processing_{step_name.lower().replace(' ', '_')}"

        try:
            result = agent.process(state)

            if result.success and result.state_updates:
                # Update state with agent results, preserving system fields
                StateManager.update_state_with_preservation(state, result.state_updates)
                logger.info(f"✅ {step_name} completed successfully")
                state.current_step = success_step

                # Log specific results for live display
                self._log_agent_results(step_name, state)

            else:
                # Agent failed - check if we can retry this step
                self._handle_step_retry(state, step_name, result.message, error_step)

            return state

        except Exception as e:
            # Exception occurred - check if we can retry this step
            self._handle_step_retry(state, step_name, str(e), error_step)
            return state

    def _log_agent_results(self, step_name: str, state: AgentState) -> None:
        """Log specific results from each agent for live display."""
        WorkflowLogger.log_agent_results(step_name, state)


    def _handle_step_retry(self, state: AgentState, step_name: str, error_message: str, error_step: str) -> bool:
        """
        Handle step retry logic. Returns True if retry was initiated, False if no retry available.

        Args:
            state: Current agent state
            step_name: Name of the step that failed
            error_message: The error message
            error_step: Base error step name for status updates

        Returns:
            True if retry was initiated, False if no more retries available
        """
        step_key = step_name.lower().replace(' ', '_')
        if step_key in state.step_retries_left and state.step_retries_left[step_key] > 0:
            # Decrement step retry counter
            state.step_retries_left[step_key] -= 1
            logger.warning(f"⚠️ {step_name} failed: {error_message}")
            logger.info(f"🔄 Retrying {step_name} (retries left: {state.step_retries_left[step_key]})")
            state.current_step = f"{error_step}_retry"
            state.last_error_type = "step_retry"
            return True
        else:
            # No more step retries, mark as failed
            logger.error(f"❌ {step_name} failed after exhausting retries: {error_message}")
            state.current_step = f"{error_step}_failed"
            return False


    def _route_after_router(self, state: AgentState) -> str:
        """Route after router based on query type."""
        return WorkflowRouter.route_after_router(state)

    def _route_after_database_identifier(self, state: AgentState) -> str:
        """Route after database identifier based on interaction mode and retry status."""
        return WorkflowRouter.route_after_database_identifier(state)

    def _route_after_database_human_feedback(self, state: AgentState) -> str:
        """Route after database human feedback based on approval status."""
        return WorkflowRouter.route_after_database_human_feedback(state)

    def _route_after_table_identifier(self, state: AgentState) -> str:
        """Route after table identifier based on interaction mode and retry status."""
        return WorkflowRouter.route_after_table_identifier(state)

    def _route_after_table_human_feedback(self, state: AgentState) -> str:
        """Route after table human feedback based on approval status."""
        return WorkflowRouter.route_after_table_human_feedback(state)

    def _route_after_validation(self, state: AgentState) -> str:
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
            self._handle_exhausted_retries(state)
            return "end"

        # Route based on issue type (retries already decremented in node if needed)
        if issue_type == "insufficient_data":
            return self._route_insufficient_data(state)
        elif issue_type == "schema_missing":
            return self._route_schema_missing(state)
        elif issue_type == "query_scope_issue":
            return self._route_query_scope_issue(state)
        elif issue_type in ("sql_generation_issue", "data_type_mismatch", "join_relationship_error"):
            return self._route_sql_issue(state, issue_type)
        else:
            return self._route_unknown_issue(state, issue_type)

    def _route_insufficient_data(self, state: AgentState) -> str:
        """Handle insufficient data routing."""
        logger.warning("⚠️ Insufficient data detected; attempting broader re-identification.")
        state.current_step = "retry_due_to_insufficient_data"
        return "database_identifier"

    def _route_schema_missing(self, state: AgentState) -> str:
        """Handle schema missing routing."""
        logger.info("🔄 Routing to table_identifier due to schema issues (missing tables/columns)")
        state.current_step = "route_to_table_identifier"
        return "table_identifier"

    def _route_query_scope_issue(self, state: AgentState) -> str:
        """Handle query scope issue routing - go back to database identification for broader perspective."""
        logger.info("🔄 Routing to database_identifier due to query_scope_issue (wrong scope/approach)")
        state.current_step = "route_to_database_identifier_scope_issue"
        return "database_identifier"

    def _route_sql_issue(self, state: AgentState, issue_type: str) -> str:
        """Handle SQL generation/planning issue routing."""
        logger.info(f"🔄 Routing to query_planner due to {issue_type}")
        state.current_step = f"route_to_query_planner_{issue_type}"
        return "query_planner"

    def _route_unknown_issue(self, state: AgentState, issue_type: str) -> str:
        """Handle unknown issue type routing."""
        logger.warning(f"⚠️ Validation failed ({issue_type or 'unknown'}), retrying from database identification.")
        state.current_step = "retry_unknown_issue"
        return "database_identifier"

    def _route_after_pipeline_step(self, state: AgentState) -> str:
        """Route after a pipeline step (column_identifier, schema_builder, etc.) checking for retries."""
        return WorkflowRouter.route_after_pipeline_step(state)

    def _route_after_metadata_step(self, state: AgentState) -> str:
        """Route after metadata agent step."""
        return WorkflowRouter.route_after_metadata_step(state)
    
    def _run_metadata_agent(self, state: AgentState) -> AgentState:
        """Process metadata queries."""
        return self._run_agent(
            state,
            self.metadata_agent,
            step_number=1,
            step_name="Metadata Agent",
            step_emoji="📊",
            success_step="metadata_completed",
            error_step="metadata_error"
        )
    
    def _run_router(self, state: AgentState) -> AgentState:
        """Route the query based on its type and requirements."""
        log_workflow_step(logger, 0, "Router", "🧭")

        # Update current step for real-time display
        state.current_step = "processing_routing"

        # If we're resuming, skip routing logic and let routing function handle it
        if getattr(state, "is_resuming", False):
            logger.info("🔄 Resuming workflow - skipping router processing")
            state.current_step = "routing_completed"
            return state

        try:
            result = self.router.process(state)

            if result.success and result.state_updates:
                StateManager.update_state_with_preservation(state, result.state_updates)
                state.current_step = "routing_completed"

                # Log routing results for live display
                if hasattr(state, 'is_metadata_query'):
                    query_type = "Metadata Query" if state.is_metadata_query else "Data Query"
                    logger.info(f"📊 Query Type: {query_type}")

                if hasattr(state, 'dialect') and state.dialect:
                    logger.info(f"🗣️ SQL Dialect: {state.dialect}")

                return state
            else:
                logger.error(f"❌ Query routing failed: {result.message}")
                state.current_step = "routing_failed"
                return state

        except Exception as e:
            logger.error(f"❌ Query routing error: {e}")
            state.current_step = "routing_error"
            return state
    
    def _run_database_identifier(self, state: AgentState) -> AgentState:
        """Identify relevant databases for the query."""
        return self._run_agent(
            state,
            self.database_identifier,
            step_number=1,
            step_name="Database Identification",
            step_emoji="🔍",
            success_step="database_identification_completed",
            error_step="database_identification"
        )

    def _run_database_human_review(self, state: AgentState) -> AgentState:
        """Get human approval for identified databases."""
        log_workflow_step(logger, 2, "Database Review", "👤")

        # Update current step for real-time display
        state.current_step = "processing_database_review"

        try:
            result = self.database_human_review.process(state)

            if result.success and result.state_updates:
                # Update state with human feedback
                StateManager.update_state_with_preservation(state, result.state_updates)
                state.current_step = "database_review_completed"

                # Log human feedback for live display
                approvals = getattr(state, 'human_approvals', {}) or {}
                approved = approvals.get('databases', False)
                feedback = getattr(state, "human_feedback", "")
                status = "✅ Approved" if approved else "🔄 Requested Changes"
                logger.info(f"👤 Database Review: {status}")
                if feedback:
                    logger.info(f"💬 Feedback: {feedback}")

                return state
            else:
                logger.error(f"❌ Database review failed: {result.message}")
                state.current_step = "database_review_failed"
                return state

        except Exception as e:
            logger.error(f"❌ Database review error: {e}")
            state.current_step = "database_review_error"
            return state

    def _run_table_human_review(self, state: AgentState) -> AgentState:
        """Get human approval for identified tables."""
        log_workflow_step(logger, 4, "Table Review", "👤")

        # Update current step for real-time display
        state.current_step = "processing_table_review"

        try:
            result = self.table_human_review.process(state)

            if result.success and result.state_updates:
                # Update state with human feedback
                StateManager.update_state_with_preservation(state, result.state_updates)
                state.current_step = "table_review_completed"

                # Log human feedback for live display
                approvals = getattr(state, 'human_approvals', {}) or {}
                approved = approvals.get('tables', False)
                feedback = getattr(state, "human_feedback", "")
                status = "✅ Approved" if approved else "🔄 Requested Changes"
                logger.info(f"👤 Table Review: {status}")
                if feedback:
                    logger.info(f"💬 Feedback: {feedback}")

                return state
            else:
                logger.error(f"❌ Table review failed: {result.message}")
                state.current_step = "table_review_failed"
                return state

        except Exception as e:
            logger.error(f"❌ Table review error: {e}")
            state.current_step = "table_review_error"
            return state
    
    def _run_table_identifier(self, state: AgentState) -> AgentState:
        """Identify relevant tables from identified databases."""
        return self._run_agent(
            state,
            self.table_identifier,
            step_number=2,
            step_name="Table Identifier",
            step_emoji="📊",
            success_step="table_identification_completed",
            error_step="table_identifier"
        )

    def _run_column_identifier(self, state: AgentState) -> AgentState:
        """Identify relevant columns from identified tables."""
        return self._run_agent(
            state,
            self.column_identifier,
            step_number=3,
            step_name="Column Identifier",
            step_emoji="🧩",
            success_step="column_identification_completed",
            error_step="column_identifier"
        )

    def _run_schema_builder(self, state: AgentState) -> AgentState:
        """Build comprehensive schema context from identified databases and tables."""
        return self._run_agent(
            state,
            self.schema_builder,
            step_number=4,
            step_name="Schema Builder",
            step_emoji="🏗️",
            success_step="schema_building_completed",
            error_step="schema_building"
        )
    
    def _run_query_planner(self, state: AgentState) -> AgentState:
        """Create logical query plan from question and schema."""
        return self._run_agent(
            state,
            self.query_planner,
            step_number=5,
            step_name="Query Planning",
            step_emoji="🧠",
            success_step="query_planning_completed",
            error_step="query_planning"
        )
    
    def _run_query_generator(self, state: AgentState) -> AgentState:
        """Generate Query from query plan and schema."""
        result_state = self._run_agent(
            state,
            self.query_generator,
            step_number=6,
            step_name="Query Generation",
            step_emoji="🔨",
            success_step="query_generation_completed",
            error_step="query_generation"
        )

        return result_state
    
    def _run_query_validator(self, state: AgentState) -> AgentState:
        """Validate the generated query."""
        result_state = self._run_agent(
            state,
            self.query_validator,
            step_number=7,
            step_name="Query Validation",
            step_emoji="🔍",
            success_step="query_validation_completed",
            error_step="query_validation"
        )

        # If validation failed and we have retries left, decrement retry counter
        if not getattr(result_state, "is_query_valid", False) and result_state.retries_left > 0:
            self._decrement_retry_and_log(result_state)

        return result_state


    def _handle_exhausted_retries(self, state: AgentState) -> None:
        """Handle the case when maximum retries are exhausted."""
        logger.warning("⚠️ Maximum retries exhausted; ending workflow with best available query.")

        feedback = getattr(state, "query_validation_feedback", {}) or {}

        if state.generated_query:
            self._update_query_with_validation_feedback(state.generated_query, feedback)
            state.user_message = "Query generated with validation issues after maximum retries. Please review the query and validation feedback carefully."

        state.current_step = "max_retries_exhausted"

    def _update_query_with_validation_feedback(self, query, feedback: dict) -> None:
        """Update query explanation with validation feedback."""
        validation_issues = []
        if feedback.get('issues'):
            validation_issues = [issue.get('description', '') for issue in feedback['issues']]

        suggestions = feedback.get('suggestions', [])

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

    def _decrement_retry_and_log(self, state: AgentState) -> None:
        """Decrement retry counter and log the change."""
        state.retries_left -= 1
        logger.info(f"🔄 Retries decremented. Retries left: {state.retries_left}")


    def _process_query_stream(self, natural_language_query: str, interaction_mode: str = "ask", callback: Optional[callable] = None):
        """
        Internal generator to process a query and yield streaming updates.
        """
        log_section_header(logger, f"🚀 PROCESSING QUERY (STREAMING): {natural_language_query[:50]}{'...' if len(natural_language_query) > 50 else ''}")
        logger.info(f"{Colors.BRIGHT_CYAN}📝 Full Query: {natural_language_query}{Colors.RESET}")
        logger.info(f"🎯 Interaction Mode: {interaction_mode}")

        # Create initial state
        initial_state = AgentState(
            natural_language_query=natural_language_query,
            interaction_mode=interaction_mode,
            current_step="workflow_started",
            retries_left=3
        )
        # Enable API mode to make HITL agents emit pending_review instead of prompting CLI
        if interaction_mode == "interactive":
            initial_state.api_mode = True

        try:
            # Generate a unique thread ID for this workflow execution
            thread_id = str(uuid.uuid4())
            logger.debug(f"Using thread ID: {thread_id}")

            # Stream the workflow execution
            for chunk in self.workflow.stream(
                initial_state,
                config={
                    "recursion_limit": 20,
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            ):
                # Extract the state from the chunk
                if isinstance(chunk, dict) and len(chunk) == 1:
                    node_name = list(chunk.keys())[0]
                    state = chunk[node_name]

                    # Convert dict to AgentState if needed
                    if isinstance(state, dict):
                        state = AgentState(**state)

                    # Call callback if provided
                    if callback:
                        callback(node_name, state)

                    # Yield the state update
                    yield state

                    # Log the step
                    step_display = self.get_current_step_display(state)
                    logger.info(f"📊 Stream update from {node_name}: {step_display}")

        except Exception as e:
            logger.error(f"❌ Workflow streaming failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            initial_state.current_step = "workflow_failed"
            yield initial_state

    def _determine_resume_node(self, state: AgentState) -> str:
        """
        Determine which node to resume from based on the current state.

        This analyzes the state to find the logical next step in the workflow.
        """
        current_step = getattr(state, 'current_step', '')

        # If workflow completed or failed, no resume needed
        if current_step in ['workflow_completed', 'workflow_failed', 'max_retries_exhausted']:
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
            "query_generation_completed": "query_validator",
            "query_validation_completed": "end",
            # Error states - retry from appropriate points
            "database_identification_failed": "database_identifier",
            "table_identifier_failed": "table_identifier",
            "column_identifier_failed": "column_identifier",
            "schema_building_failed": "schema_builder",
            "query_planning_failed": "query_planner",
            "query_generation_failed": "query_generator",
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
