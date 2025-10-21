"""
Metadata Agent for handling metadata queries.

This agent handles queries that ask for information about the database structure,
such as listing tables, databases, columns, etc. It uses SQL Knowledge Base retrieval
to fetch relevant schema chunks and generates natural language responses.
"""

import logging
from typing import List

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from models.models import AgentState, AgentResult, AgentType
from tools import (
    semantic_search,
    search_by_database,
    search_by_table,
    get_all_databases,
    get_tables_in_database,
    count_databases,
    count_tables_in_database,
    search_tables_in_databases,
    complex_filter_search,
    get_columns_by_table
)

logger = logging.getLogger(__name__)


class MetadataAgent(BaseAgent):
    """Agent responsible for handling metadata queries."""

    def __init__(self, model_wrapper, tools: List = None, retriever=None):
        super().__init__(AgentType.METADATA_AGENT, model_wrapper)

        self.tools = tools if tools is not None else [
            semantic_search,
            search_by_database,
            search_by_table,
            get_all_databases,
            get_tables_in_database,
            count_databases,
            count_tables_in_database,
            search_tables_in_databases,
            complex_filter_search,
            get_columns_by_table
        ]
        self.retriever = retriever
        self.tool_names = [tool.name for tool in self.tools]

    def process(self, state: AgentState) -> AgentResult:
        """Process metadata queries to provide database structure information."""
        logger.info(f"📊 {self.name}: Processing metadata query")

        try:
            # Validate prerequisites
            validation_error = AgentUtils.validate_query_text(state)
            if validation_error:
                return validation_error

            # Use tool-enabled LLM to intelligently retrieve schema information
            response = self._process_query_with_tools(state.natural_language_query)

            return self._create_success_result(response, state.natural_language_query)

        except Exception as e:
            logger.error(f"❌ Metadata query processing failed: {e}")
            return AgentUtils.create_error_result(str(e))


    def _create_success_result(self, response: str, query: str) -> AgentResult:
        """Create success result with natural language response."""

        state_updates = {
            "metadata_response": f"Query: {query}\n\nResponse: {response}",
            "metadata_type": "schema_info",
            "current_step": "metadata_completed"
        }

        logger.info("✅ Metadata query processing completed successfully")
        return AgentResult(
            success=True,
            message="Metadata query processed successfully",
            state_updates=state_updates
        )
    
    def _create_metadata_tool_system_prompt(self) -> str:
        """Create a comprehensive system prompt with detailed tool usage guidance."""

        return (
            "You are an expert database metadata assistant.\n\n"

            "## 🚨 CRITICAL RULES:\n"
            f"**TOOLS ({len(self.tool_names)}):** {', '.join(self.tool_names)}\n"
            "**NEVER call tools that don't exist!** Calling 'assistant' or any non-listed tool will FAIL.\n\n"

            "## 📋 COLUMNS QUERY WORKFLOW:\n"
            "**For 'list columns in TABLE':**\n"
            "1. `complex_filter_search('table_name', {'chunk_type': 'table'})` → finds table & database\n"
            "2. `get_columns_by_table('database_name', ['table_name'])` → gets column details\n"
            "3. Respond with results\n\n"

            "**EXAMPLE:** 'list columns in user_state_transition_audit'\n"
            "→ complex_filter_search('user_state_transition_audit', {'chunk_type': 'table'})\n"
            "→ get_columns_by_table('wallet', ['user_state_transition_audit'])\n\n"

            "## 🛠️ TOOLS QUICK REFERENCE:\n\n"
            "**DISCOVERY:**\n"
            "• `get_all_databases()` - List all databases\n"
            "• `get_tables_in_database(db)` - List tables in database\n"
            "• `count_databases()` - Count total databases (efficient)\n"
            "• `count_tables_in_database(db)` - Count tables in database (efficient)\n\n"

            "**SEARCH:**\n"
            "• `semantic_search(query)` - Broad search across all data\n"
            "• `search_by_database(query, db)` - Search within specific database\n"
            "• `complex_filter_search(query, filters)` - Advanced filtered search\n\n"

            "**COLUMNS:**\n"
            "• `get_columns_by_table(db, [tables])` - Get detailed column info\n\n"

            "## 🎯 QUICK DECISIONS:\n"
            "**Columns in table:** complex_filter_search → get_columns_by_table\n"
            "**Tables in database:** get_tables_in_database\n"
            "**Count tables in database:** count_tables_in_database\n"
            "**Count all databases:** count_databases\n"
            "**Find anything:** semantic_search\n\n"

            "## 🚫 FORBIDDEN:\n"
            "• Calling non-existent tools (assistant, clarify, help)\n"
            "• Making up tool names\n"
            "• Skipping workflow steps\n\n"

            "**COLUMN TYPES:** PRI=Primary Key, UNI=Unique, MUL=Index"
        )


    def _process_query_with_tools(self, query: str) -> str:
        """
        Process a metadata query using LLM tool calling and return the final response text.

        Args:
            query: The user's natural language query

        Returns:
            Final LLM response as a string
        """
        try:
            system_message = self._create_metadata_tool_system_prompt()

            response = self.generate_with_llm(
                system_message=system_message,
                human_message=query,
                tools=self.tools,
                max_length=2048,
                temperature=0.2,
                max_tool_iterations=10
            )

            # Best-effort normalize to string
            try:
                response_text = response.strip() if isinstance(response, str) else str(response)
            except Exception:
                response_text = str(response)

            return response_text

        except Exception as e:
            logger.error(f"Error in metadata tool processing: {e}")
            return f"Unable to retrieve metadata at the moment. Error: {e}"
