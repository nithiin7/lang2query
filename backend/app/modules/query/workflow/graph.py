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
7. SQL Safety Guard - deterministic (non-LLM) check that the generated SQL
   is a single read-only SELECT; a failure here is a hard stop, not routed
   through the semantic retry loop
8. Query Validator Agent - validates the generated query semantically

Graph wiring and node dispatch only. Routing decisions live in `router.py`,
resume-point resolution in `resume.py`, and presentation/logging in
`display.py` and `state.py`.
"""

import functools
import logging
import uuid
from typing import Any, Dict, Iterator, Optional, Union

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ai.llm import ModelWrapper
from ai.retrieve_sql_kb import SQLKnowledgeBaseRetriever
from core.config import COLLECTION_NAME, EMBEDDING_MODEL_PATH, KB_DIRECTORY
from core.logging import Colors, log_section_header, log_workflow_step
from modules.query.agents import (
    AgentState,
    ColumnIdentifier,
    DatabaseIdentifierAgent,
    HumanInTheLoopAgent,
    MetadataAgent,
    QueryGeneratorAgent,
    QueryPlannerAgent,
    QueryValidatorAgent,
    RouterAgent,
    SchemaBuilderAgent,
    SQLSafetyGuardAgent,
    TableIdentifier,
)

from .display import WorkflowDisplay, WorkflowLogger
from .resume import ResumeRouter
from .router import WorkflowRouter
from .state import StateManager

logger = logging.getLogger(__name__)


# Config for the pipeline nodes that share the standard run/retry/log pattern
# (agent attribute on Text2QueryWorkflow, log step number, display name, and
# the current_step values to set on success/error). Nodes with real branching
# logic (router, the two human-review nodes, query_validator's extra retry
# bookkeeping) are handled by their own methods below instead.
PIPELINE_NODE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "metadata_agent": dict(
        agent_attr="metadata_agent",
        step_number=1,
        step_name="Metadata Agent",
        success_step="metadata_completed",
        error_step="metadata_error",
    ),
    "database_identifier": dict(
        agent_attr="database_identifier",
        step_number=1,
        step_name="Database Identification",
        success_step="database_identification_completed",
        error_step="database_identification",
    ),
    "table_identifier": dict(
        agent_attr="table_identifier",
        step_number=2,
        step_name="Table Identifier",
        success_step="table_identification_completed",
        error_step="table_identifier",
    ),
    "column_identifier": dict(
        agent_attr="column_identifier",
        step_number=3,
        step_name="Column Identifier",
        success_step="column_identification_completed",
        error_step="column_identifier",
    ),
    "schema_builder": dict(
        agent_attr="schema_builder",
        step_number=4,
        step_name="Schema Builder",
        success_step="schema_building_completed",
        error_step="schema_building",
    ),
    "query_planner": dict(
        agent_attr="query_planner",
        step_number=5,
        step_name="Query Planning",
        success_step="query_planning_completed",
        error_step="query_planning",
    ),
    "query_generator": dict(
        agent_attr="query_generator",
        step_number=6,
        step_name="Query Generation",
        success_step="query_generation_completed",
        error_step="query_generation",
    ),
    "sql_safety_guard": dict(
        agent_attr="sql_safety_guard",
        step_number=6,
        step_name="Sql Safety Guard",
        success_step="sql_safety_check_completed",
        error_step="sql_safety_guard",
    ),
    "query_validator": dict(
        agent_attr="query_validator",
        step_number=7,
        step_name="Query Validation",
        success_step="query_validation_completed",
        error_step="query_validation",
    ),
}


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
                collection_name=COLLECTION_NAME,
            )
            logger.info("Shared retriever initialized successfully")
        except Exception as e:
            logger.warning(f"Shared retriever initialization failed: {e}")

        # Initialize all agents
        self.router = RouterAgent(model)
        self.metadata_agent = MetadataAgent(model, retriever=self.retriever)
        self.database_identifier = DatabaseIdentifierAgent(
            model, retriever=self.retriever
        )
        self.database_human_review = HumanInTheLoopAgent(
            model,
            confirmation_type="databases",
            data_source="relevant_databases",
            retriever=self.retriever,
        )
        self.table_human_review = HumanInTheLoopAgent(
            model,
            confirmation_type="tables",
            data_source="relevant_tables",
            retriever=self.retriever,
        )
        self.table_identifier = TableIdentifier(model, retriever=self.retriever)
        self.column_identifier = ColumnIdentifier(model, retriever=self.retriever)
        self.schema_builder = SchemaBuilderAgent(model, retriever=self.retriever)
        self.query_planner = QueryPlannerAgent(model, retriever=self.retriever)
        self.query_generator = QueryGeneratorAgent(model, retriever=self.retriever)
        self.sql_safety_guard = SQLSafetyGuardAgent(model)
        self.query_validator = QueryValidatorAgent(model, retriever=self.retriever)

        # Create the workflow graph
        self.checkpointer = MemorySaver()
        self.workflow = self._create_workflow()
        logger.info("Text2Query workflow initialized successfully")

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
            return self._process_query_stream(
                natural_language_query, interaction_mode, callback
            )

        log_section_header(
            logger,
            f"PROCESSING QUERY: {natural_language_query[:50]}{'...' if len(natural_language_query) > 50 else ''}",
        )
        logger.info(
            f"{Colors.BRIGHT_CYAN}Full Query: {natural_language_query}{Colors.RESET}"
        )
        logger.info(f"Interaction Mode: {interaction_mode}")

        initial_state = self._create_initial_state(
            natural_language_query, interaction_mode
        )

        try:
            thread_id = str(uuid.uuid4())
            logger.debug(f"Using thread ID: {thread_id}")

            # Run the workflow with recursion limit to prevent infinite loops
            final_state = self.workflow.invoke(
                initial_state,
                config={
                    "recursion_limit": 20,
                    "configurable": {"thread_id": thread_id},
                },
            )

            # Handle potential dict return (LangGraph sometimes returns dict)
            if isinstance(final_state, dict):
                logger.debug("Converting dict response to AgentState")
                final_state = AgentState(**final_state)

            return final_state

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
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
            start_node = ResumeRouter.determine_resume_node(state)
            logger.info(f"Resuming workflow from node: {start_node}")

            # Mark state as resuming to modify routing behavior
            state.is_resuming = True
            state.resume_start_node = start_node

            # Use the original workflow - router will route directly to start_node
            for chunk in self.workflow.stream(
                state,
                config={
                    "recursion_limit": 20,
                    "configurable": {"thread_id": thread_id},
                },
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
                    logger.info(f"Resume update from {node_name}: {step_display}")

        except Exception as e:
            logger.error(f"Workflow resume failed: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            state.current_step = "workflow_failed"
            yield state

    def get_current_step_display(self, state: AgentState) -> str:
        """Get user-friendly display text for current step."""
        return WorkflowDisplay.get_current_step_display(state)

    def get_workflow_summary(self, state: AgentState) -> Dict[str, Any]:
        """Get a comprehensive summary of the workflow execution."""
        return WorkflowDisplay.get_workflow_summary(state)

    def _create_initial_state(
        self, natural_language_query: str, interaction_mode: str
    ) -> AgentState:
        """Build the AgentState a fresh workflow run starts from."""
        return AgentState(
            natural_language_query=natural_language_query,
            interaction_mode=interaction_mode,
            current_step="workflow_started",
            retries_left=3,
        )

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with the refined architecture."""
        workflow = StateGraph(AgentState)

        # Define agent nodes with their handlers
        agents = [
            ("router", self._run_router),
            (
                "metadata_agent",
                functools.partial(self._run_pipeline_node, "metadata_agent"),
            ),
            (
                "database_identifier",
                functools.partial(self._run_pipeline_node, "database_identifier"),
            ),
            ("database_human_review", self._run_database_human_review),
            (
                "table_identifier",
                functools.partial(self._run_pipeline_node, "table_identifier"),
            ),
            ("table_human_review", self._run_table_human_review),
            (
                "column_identifier",
                functools.partial(self._run_pipeline_node, "column_identifier"),
            ),
            (
                "schema_builder",
                functools.partial(self._run_pipeline_node, "schema_builder"),
            ),
            (
                "query_planner",
                functools.partial(self._run_pipeline_node, "query_planner"),
            ),
            (
                "query_generator",
                functools.partial(self._run_pipeline_node, "query_generator"),
            ),
            (
                "sql_safety_guard",
                functools.partial(self._run_pipeline_node, "sql_safety_guard"),
            ),
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
            "end": END,
        }

        workflow.add_conditional_edges(
            "router", WorkflowRouter.route_after_router, router_targets
        )

        # Metadata flow
        workflow.add_edge("metadata_agent", END)

        # Conditional routing after database_identifier based on interaction mode
        workflow.add_conditional_edges(
            "database_identifier",
            WorkflowRouter.route_after_database_identifier,
            {
                "database_human_review": "database_human_review",
                "table_identifier": "table_identifier",
            },
        )

        # Conditional routing after database human review
        workflow.add_conditional_edges(
            "database_human_review",
            WorkflowRouter.route_after_database_human_feedback,
            {
                "database_human_review": "database_human_review",  # Show updated list after modifications
                "database_identifier": "database_identifier",  # Re-identify if rejected
                "table_identifier": "table_identifier",  # Proceed if approved
            },
        )

        # Conditional routing after table_identifier based on interaction mode
        workflow.add_conditional_edges(
            "table_identifier",
            WorkflowRouter.route_after_table_identifier,
            {
                "table_human_review": "table_human_review",
                "column_identifier": "column_identifier",
            },
        )

        # Conditional routing after table human review
        workflow.add_conditional_edges(
            "table_human_review",
            WorkflowRouter.route_after_table_human_feedback,
            {
                "table_human_review": "table_human_review",  # Show updated list after modifications
                "table_identifier": "table_identifier",  # Re-identify if rejected
                "column_identifier": "column_identifier",  # Proceed if approved
            },
        )

        # Add conditional edges for the main processing pipeline to handle retries
        workflow.add_conditional_edges(
            "column_identifier",
            WorkflowRouter.route_after_pipeline_step,
            {
                "column_identifier": "column_identifier",  # Retry
                "schema_builder": "schema_builder",  # Continue
                END: END,  # Fail
            },
        )

        workflow.add_conditional_edges(
            "schema_builder",
            WorkflowRouter.route_after_pipeline_step,
            {
                "schema_builder": "schema_builder",  # Retry
                "query_planner": "query_planner",  # Continue
                END: END,  # Fail
            },
        )

        workflow.add_conditional_edges(
            "query_planner",
            WorkflowRouter.route_after_pipeline_step,
            {
                "query_planner": "query_planner",  # Retry
                "query_generator": "query_generator",  # Continue
                END: END,  # Fail
            },
        )

        workflow.add_conditional_edges(
            "query_generator",
            WorkflowRouter.route_after_pipeline_step,
            {
                "query_generator": "query_generator",  # Retry
                "sql_safety_guard": "sql_safety_guard",  # Continue
                END: END,  # Fail
            },
        )

        # SQL safety guard: deterministic, non-LLM check. A failure here is a
        # hard stop (END) - it does NOT feed into the semantic retry loop below.
        # See sql_safety_guard.py for why safety failures aren't treated like
        # semantic validation failures.
        workflow.add_conditional_edges(
            "sql_safety_guard",
            WorkflowRouter.route_after_sql_safety_guard,
            {
                "query_validator": "query_validator",  # Safe: continue to semantic validation
                END: END,  # Unsafe: hard fail, no retry
            },
        )

        # Metadata agent routing
        workflow.add_conditional_edges(
            "metadata_agent",
            WorkflowRouter.route_after_metadata_step,
            {
                "metadata_agent": "metadata_agent",  # Retry
                END: END,  # Continue or fail
            },
        )

        # Validation retry logic
        workflow.add_conditional_edges(
            "query_validator",
            WorkflowRouter.route_after_validation,
            {
                "database_identifier": "database_identifier",
                "table_identifier": "table_identifier",
                "query_planner": "query_planner",
                "end": END,
            },
        )

        return workflow.compile(checkpointer=self.checkpointer)

    def _run_agent(
        self,
        state: AgentState,
        agent,
        step_number: int,
        step_name: str,
        success_step: str,
        error_step: str,
    ) -> AgentState:
        """Common method to run any agent with standardized error handling and logging."""
        log_workflow_step(logger, step_number, step_name)

        # Update current step for real-time display
        state.current_step = f"processing_{step_name.lower().replace(' ', '_')}"

        try:
            result = agent.process(state)

            if result.success and result.state_updates:
                # Update state with agent results, preserving system fields
                StateManager.update_state_with_preservation(state, result.state_updates)
                logger.info(f"{step_name} completed successfully")
                state.current_step = success_step

                # Log specific results for live display
                WorkflowLogger.log_agent_results(step_name, state)

            else:
                # Agent failed - check if we can retry this step
                self._handle_step_retry(state, step_name, result.message, error_step)

            return state

        except Exception as e:
            # Exception occurred - check if we can retry this step
            self._handle_step_retry(state, step_name, str(e), error_step)
            return state

    def _run_pipeline_node(self, node_name: str, state: AgentState) -> AgentState:
        """Run a pipeline node that follows the standard run/retry/log pattern.

        `node_name` selects the agent instance and logging/state-step names
        from `PIPELINE_NODE_CONFIGS`. Nodes with extra branching (router,
        human-review nodes, query_validator's retry bookkeeping) have their
        own `_run_*` methods instead of going through here.
        """
        cfg = PIPELINE_NODE_CONFIGS[node_name]
        agent = getattr(self, cfg["agent_attr"])
        return self._run_agent(
            state,
            agent,
            step_number=cfg["step_number"],
            step_name=cfg["step_name"],
            success_step=cfg["success_step"],
            error_step=cfg["error_step"],
        )

    def _handle_step_retry(
        self, state: AgentState, step_name: str, error_message: str, error_step: str
    ) -> bool:
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
        step_key = step_name.lower().replace(" ", "_")
        if (
            step_key in state.step_retries_left
            and state.step_retries_left[step_key] > 0
        ):
            # Decrement step retry counter
            state.step_retries_left[step_key] -= 1
            logger.warning(f"{step_name} failed: {error_message}")
            logger.info(
                f"Retrying {step_name} (retries left: {state.step_retries_left[step_key]})"
            )
            state.current_step = f"{error_step}_retry"
            state.last_error_type = "step_retry"
            return True
        else:
            # No more step retries, mark as failed
            logger.error(
                f"{step_name} failed after exhausting retries: {error_message}"
            )
            state.current_step = f"{error_step}_failed"
            return False

    def _run_router(self, state: AgentState) -> AgentState:
        """Route the query based on its type and requirements."""
        log_workflow_step(logger, 0, "Router")

        # Update current step for real-time display
        state.current_step = "processing_routing"

        # If we're resuming, skip routing logic and let routing function handle it
        if getattr(state, "is_resuming", False):
            logger.info("Resuming workflow - skipping router processing")
            state.current_step = "routing_completed"
            return state

        try:
            result = self.router.process(state)

            if result.success and result.state_updates:
                StateManager.update_state_with_preservation(state, result.state_updates)
                state.current_step = "routing_completed"

                # Log routing results for live display
                if hasattr(state, "is_metadata_query"):
                    query_type = (
                        "Metadata Query" if state.is_metadata_query else "Data Query"
                    )
                    logger.info(f"Query Type: {query_type}")

                if hasattr(state, "dialect") and state.dialect:
                    logger.info(f"SQL Dialect: {state.dialect}")

                return state
            else:
                logger.error(f"Query routing failed: {result.message}")
                state.current_step = "routing_failed"
                return state

        except Exception as e:
            logger.error(f"Query routing error: {e}")
            state.current_step = "routing_error"
            return state

    def _run_database_human_review(self, state: AgentState) -> AgentState:
        """Get human approval for identified databases."""
        log_workflow_step(logger, 2, "Database Review")

        # Update current step for real-time display
        state.current_step = "processing_database_review"

        try:
            result = self.database_human_review.process(state)

            if result.success and result.state_updates:
                # Update state with human feedback
                StateManager.update_state_with_preservation(state, result.state_updates)
                state.current_step = "database_review_completed"

                # Log human feedback for live display
                approvals = getattr(state, "human_approvals", {}) or {}
                approved = approvals.get("databases", False)
                feedback = getattr(state, "human_feedback", "")
                status = "Approved" if approved else "Requested Changes"
                logger.info(f"Database Review: {status}")
                if feedback:
                    logger.info(f"Feedback: {feedback}")

                return state
            else:
                logger.error(f"Database review failed: {result.message}")
                state.current_step = "database_review_failed"
                return state

        except Exception as e:
            logger.error(f"Database review error: {e}")
            state.current_step = "database_review_error"
            return state

    def _run_table_human_review(self, state: AgentState) -> AgentState:
        """Get human approval for identified tables."""
        log_workflow_step(logger, 4, "Table Review")

        # Update current step for real-time display
        state.current_step = "processing_table_review"

        try:
            result = self.table_human_review.process(state)

            if result.success and result.state_updates:
                # Update state with human feedback
                StateManager.update_state_with_preservation(state, result.state_updates)
                state.current_step = "table_review_completed"

                # Log human feedback for live display
                approvals = getattr(state, "human_approvals", {}) or {}
                approved = approvals.get("tables", False)
                feedback = getattr(state, "human_feedback", "")
                status = "Approved" if approved else "Requested Changes"
                logger.info(f"Table Review: {status}")
                if feedback:
                    logger.info(f"Feedback: {feedback}")

                return state
            else:
                logger.error(f"Table review failed: {result.message}")
                state.current_step = "table_review_failed"
                return state

        except Exception as e:
            logger.error(f"Table review error: {e}")
            state.current_step = "table_review_error"
            return state

    def _run_query_validator(self, state: AgentState) -> AgentState:
        """Validate the generated query."""
        result_state = self._run_pipeline_node("query_validator", state)

        # If validation failed and we have retries left, decrement retry counter
        if (
            not getattr(result_state, "is_query_valid", False)
            and result_state.retries_left > 0
        ):
            WorkflowRouter.decrement_retry_and_log(result_state)

        return result_state

    def _process_query_stream(
        self,
        natural_language_query: str,
        interaction_mode: str = "ask",
        callback: Optional[callable] = None,
    ):
        """
        Internal generator to process a query and yield streaming updates.
        """
        log_section_header(
            logger,
            f"PROCESSING QUERY (STREAMING): {natural_language_query[:50]}{'...' if len(natural_language_query) > 50 else ''}",
        )
        logger.info(
            f"{Colors.BRIGHT_CYAN}Full Query: {natural_language_query}{Colors.RESET}"
        )
        logger.info(f"Interaction Mode: {interaction_mode}")

        initial_state = self._create_initial_state(
            natural_language_query, interaction_mode
        )
        # Enable API mode to make HITL agents emit pending_review instead of prompting CLI
        if interaction_mode == "interactive":
            initial_state.api_mode = True

        try:
            thread_id = str(uuid.uuid4())
            logger.debug(f"Using thread ID: {thread_id}")

            # Stream the workflow execution
            for chunk in self.workflow.stream(
                initial_state,
                config={
                    "recursion_limit": 20,
                    "configurable": {"thread_id": thread_id},
                },
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
                    logger.info(f"Stream update from {node_name}: {step_display}")

        except Exception as e:
            logger.error(f"Workflow streaming failed: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            initial_state.current_step = "workflow_failed"
            yield initial_state
