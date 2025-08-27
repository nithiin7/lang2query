"""LangGraph workflow for text-to-query conversion."""

from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph

from ..agents.query_agent import QueryGenerationAgent, SQLQuery
from ..config import settings
from ..utils.db_parser import MarkdownDBParser
from ..utils.logger import logger


class WorkflowState(TypedDict, total=False):
    """State for the query generation workflow."""

    messages: Annotated[List[BaseMessage], "Chat messages"]
    user_request: Annotated[str, "The original user request"]
    database_schema: Annotated[str, "Database schema information"]
    generated_query: Annotated[Any, "The generated SQL query"]
    validation_result: Annotated[Dict[str, Any], "Query validation results"]
    final_response: Annotated[str, "Final response to user"]


def parse_schema_node(state: WorkflowState) -> WorkflowState:
    """Parse and extract database schema information."""
    try:
        parser = MarkdownDBParser("sample_db_metadata.md")
        schema_summary = parser.get_schema_summary()

        logger.info("Successfully parsed database schema")

        return {**state, "database_schema": schema_summary}
    except Exception as e:
        logger.error(f"Error parsing schema: {e}")
        return {**state, "database_schema": f"Error parsing schema: {str(e)}"}


def generate_query_node(state: WorkflowState) -> WorkflowState:
    """Generate SQL query from user request using the query agent."""
    try:
        # Initialize the query generation agent
        agent = QueryGenerationAgent(
            api_key=settings.openai_api_key, db_metadata_path="sample_db_metadata.md"
        )

        # Generate the query
        sql_query = agent.generate_query(state["user_request"])

        logger.info(f"Generated query: {sql_query.query}")

        return {**state, "generated_query": sql_query}
    except Exception as e:
        logger.error(f"Error generating query: {e}")
        # Create a fallback query
        fallback_query = SQLQuery(
            query="-- Error generating query",
            explanation=f"Failed to generate query: {str(e)}",
            tables_used=[],
            confidence=0.0,
        )

        return {**state, "generated_query": fallback_query}


def validate_query_node(state: WorkflowState) -> WorkflowState:
    """Validate the generated SQL query."""
    try:
        agent = QueryGenerationAgent(
            api_key=settings.openai_api_key, db_metadata_path="sample_db_metadata.md"
        )

        generated = state.get("generated_query")
        query_str = generated.query if generated is not None else ""
        validation_result = agent.validate_query(query_str)

        logger.info(f"Query validation completed: {validation_result}")

        return {**state, "validation_result": validation_result}
    except Exception as e:
        logger.error(f"Error validating query: {e}")
        return {
            **state,
            "validation_result": {
                "is_valid": False,
                "warnings": [],
                "errors": [f"Validation error: {str(e)}"],
            },
        }


def format_response_node(state: WorkflowState) -> WorkflowState:
    """Format the final response for the user."""
    try:
        query = state.get("generated_query")
        if query is None:
            # Ensure query exists for following accesses
            query = SQLQuery(
                query="-- No query generated",
                explanation="No query was generated prior to formatting",
                tables_used=[],
                confidence=0.0,
            )
        validation = state["validation_result"]

        # Build the response
        response_parts = []

        # Add the SQL query
        response_parts.append("## Generated SQL Query")
        response_parts.append(f"```sql\n{query.query}\n```")

        # Add explanation
        response_parts.append("## Explanation")
        response_parts.append(query.explanation)

        # Add metadata
        response_parts.append("## Query Details")
        response_parts.append(f"- **Tables Used:** {', '.join(query.tables_used)}")
        response_parts.append(f"- **Confidence:** {query.confidence:.2%}")

        # Add validation results
        if validation.get("warnings"):
            response_parts.append("## ⚠️ Warnings")
            for warning in validation["warnings"]:
                response_parts.append(f"- {warning}")

        if validation.get("errors"):
            response_parts.append("## ❌ Errors")
            for error in validation["errors"]:
                response_parts.append(f"- {error}")

        # Add schema context
        response_parts.append("## Database Schema Context")
        response_parts.append("```")
        response_parts.append(state["database_schema"])
        response_parts.append("```")

        final_response = "\n\n".join(response_parts)

        logger.info("Formatted final response")

        return {**state, "final_response": final_response}
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return {**state, "final_response": f"Error formatting response: {str(e)}"}


def should_continue(state: WorkflowState) -> str:
    """Determine the next step in the workflow."""
    # Check if we have a valid query
    generated = state.get("generated_query")
    if isinstance(generated, SQLQuery):
        if generated.confidence > 0.5:
            return "validate_query"
        else:
            return "format_response"

    return "generate_query"


def build_query_workflow() -> StateGraph:
    """Build the LangGraph workflow for query generation."""

    # Create the workflow
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("parse_schema", parse_schema_node)
    workflow.add_node("generate_query", generate_query_node)
    workflow.add_node("validate_query", validate_query_node)
    workflow.add_node("format_response", format_response_node)

    # Set entry point
    workflow.set_entry_point("parse_schema")

    # Add conditional edges
    workflow.add_conditional_edges(
        "parse_schema",
        should_continue,
        {
            "generate_query": "generate_query",
            "validate_query": "validate_query",
            "format_response": "format_response",
        },
    )

    workflow.add_edge("generate_query", "validate_query")
    workflow.add_edge("validate_query", "format_response")
    workflow.add_edge("format_response", END)

    # Compile the workflow
    return workflow.compile()


def run_query_workflow(user_request: str) -> str:
    """Run the complete query generation workflow."""
    try:
        # Build the workflow
        workflow = build_query_workflow()

        # Initialize the state
        initial_state: Dict[str, Any] = {
            "messages": [HumanMessage(content=user_request)],
            "user_request": user_request,
            "database_schema": "",
            "generated_query": None,
            "validation_result": {},
            "final_response": "",
        }

        # Run the workflow
        logger.info(f"Starting workflow for request: {user_request}")
        result = workflow.invoke(initial_state)

        logger.info("Workflow completed successfully")

        return result["final_response"]

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return f"Error executing workflow: {str(e)}"
