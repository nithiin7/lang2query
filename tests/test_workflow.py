"""Tests for the workflow module."""

from unittest.mock import Mock, patch

from langchain_core.messages import HumanMessage

from lang2query.agents.query_agent import SQLQuery
from lang2query.core.workflow import (
    WorkflowState,
    build_query_workflow,
    format_response_node,
    generate_query_node,
    parse_schema_node,
    run_query_workflow,
    should_continue,
    validate_query_node,
)


class TestWorkflowState:
    """Test the WorkflowState TypedDict."""

    def test_workflow_state_structure(self):
        """Test that WorkflowState has the expected structure."""
        state = WorkflowState(
            messages=[HumanMessage(content="test")],
            user_request="test request",
            database_schema="test schema",
            generated_query=None,
            validation_result={},
            final_response="",
        )

        assert "messages" in state
        assert "user_request" in state
        assert "database_schema" in state
        assert "generated_query" in state
        assert "validation_result" in state
        assert "final_response" in state


class TestWorkflowNodes:
    """Test individual workflow nodes."""

    def test_parse_schema_node_success(self):
        """Test successful schema parsing."""
        state = WorkflowState(
            messages=[],
            user_request="test",
            database_schema="",
            generated_query=None,
            validation_result={},
            final_response="",
        )

        with patch("lang2query.core.workflow.MarkdownDBParser") as mock_parser:
            mock_instance = Mock()
            mock_instance.get_schema_summary.return_value = "Parsed schema"
            mock_parser.return_value = mock_instance

            result = parse_schema_node(state)

            assert result["database_schema"] == "Parsed schema"

    def test_parse_schema_node_error(self):
        """Test schema parsing error handling."""
        state = WorkflowState(
            messages=[],
            user_request="test",
            database_schema="",
            generated_query=None,
            validation_result={},
            final_response="",
        )

        with patch("lang2query.core.workflow.MarkdownDBParser") as mock_parser:
            mock_parser.side_effect = Exception("Parse error")

            result = parse_schema_node(state)

            assert "Error parsing schema" in result["database_schema"]

    def test_generate_query_node_success(self):
        """Test successful query generation."""
        state = WorkflowState(
            messages=[],
            user_request="Show me users",
            database_schema="test schema",
            generated_query=None,
            validation_result={},
            final_response="",
        )

        mock_query = SQLQuery(
            query="SELECT * FROM users",
            explanation="Test query",
            tables_used=["users"],
            confidence=0.9,
        )

        with patch("lang2query.core.workflow.QueryGenerationAgent") as mock_agent_class:
            mock_agent = Mock()
            mock_agent.generate_query.return_value = mock_query
            mock_agent_class.return_value = mock_agent

            result = generate_query_node(state)

            assert result["generated_query"] == mock_query

    def test_generate_query_node_error(self):
        """Test query generation error handling."""
        state = WorkflowState(
            messages=[],
            user_request="Show me users",
            database_schema="test schema",
            generated_query=None,
            validation_result={},
            final_response="",
        )

        with patch("lang2query.core.workflow.QueryGenerationAgent") as mock_agent_class:
            mock_agent_class.side_effect = Exception("Agent error")

            result = generate_query_node(state)

            assert result["generated_query"].query == "-- Error generating query"
            assert result["generated_query"].confidence == 0.0

    def test_validate_query_node_success(self):
        """Test successful query validation."""
        mock_query = SQLQuery(
            query="SELECT * FROM users",
            explanation="Test query",
            tables_used=["users"],
            confidence=0.9,
        )

        state = WorkflowState(
            messages=[],
            user_request="test",
            database_schema="test schema",
            generated_query=mock_query,
            validation_result={},
            final_response="",
        )

        with patch("lang2query.core.workflow.QueryGenerationAgent") as mock_agent_class:
            mock_agent = Mock()
            mock_agent.validate_query.return_value = {
                "is_valid": True,
                "warnings": [],
                "errors": [],
            }
            mock_agent_class.return_value = mock_agent

            result = validate_query_node(state)

            assert result["validation_result"]["is_valid"] is True

    def test_format_response_node_success(self):
        """Test successful response formatting."""
        mock_query = SQLQuery(
            query="SELECT * FROM users",
            explanation="Test query",
            tables_used=["users"],
            confidence=0.9,
        )

        state = WorkflowState(
            messages=[],
            user_request="test",
            database_schema="test schema",
            generated_query=mock_query,
            validation_result={"is_valid": True, "warnings": [], "errors": []},
            final_response="",
        )

        result = format_response_node(state)

        assert "## Generated SQL Query" in result["final_response"]
        assert "SELECT * FROM users" in result["final_response"]
        assert "## Explanation" in result["final_response"]
        assert "Test query" in result["final_response"]


class TestWorkflowLogic:
    """Test workflow logic and routing."""

    def test_should_continue_with_valid_query(self):
        """Test routing logic with valid query."""
        mock_query = SQLQuery(
            query="SELECT * FROM users",
            explanation="Test query",
            tables_used=["users"],
            confidence=0.9,
        )

        state = WorkflowState(
            messages=[],
            user_request="test",
            database_schema="test schema",
            generated_query=mock_query,
            validation_result={},
            final_response="",
        )

        next_step = should_continue(state)
        assert next_step == "validate_query"

    def test_should_continue_with_low_confidence(self):
        """Test routing logic with low confidence query."""
        mock_query = SQLQuery(
            query="SELECT * FROM users",
            explanation="Test query",
            tables_used=["users"],
            confidence=0.3,
        )

        state = WorkflowState(
            messages=[],
            user_request="test",
            database_schema="test schema",
            generated_query=mock_query,
            validation_result={},
            final_response="",
        )

        next_step = should_continue(state)
        assert next_step == "format_response"

    def test_should_continue_no_query(self):
        """Test routing logic with no query."""
        state = WorkflowState(
            messages=[],
            user_request="test",
            database_schema="test schema",
            generated_query=None,
            validation_result={},
            final_response="",
        )

        next_step = should_continue(state)
        assert next_step == "generate_query"


class TestWorkflowIntegration:
    """Test workflow integration."""

    def test_build_query_workflow(self):
        """Test workflow building."""
        workflow = build_query_workflow()

        # Check that workflow is compiled
        assert hasattr(workflow, "invoke")

    @patch("lang2query.core.workflow.build_query_workflow")
    def test_run_query_workflow_success(self, mock_build):
        """Test successful workflow execution."""
        mock_workflow = Mock()
        mock_workflow.invoke.return_value = {"final_response": "Test response"}
        mock_build.return_value = mock_workflow

        result = run_query_workflow("Show me users")

        assert result == "Test response"
        mock_workflow.invoke.assert_called_once()

    @patch("lang2query.core.workflow.build_query_workflow")
    def test_run_query_workflow_error(self, mock_build):
        """Test workflow execution error handling."""
        mock_build.side_effect = Exception("Workflow error")

        result = run_query_workflow("Show me users")

        assert "Error executing workflow" in result
