"""
Table Identifier Agent for the text2query system.

Uses retriever to identify relevant tables from the databases selected
by the previous database_identifier agent.
"""

import logging
from typing import List

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from utils import ChunkParsers
from models.models import AgentState, AgentResult, AgentType, TableSelection

logger = logging.getLogger(__name__)


class TableIdentifier(BaseAgent):
    """Agent responsible for identifying relevant tables from selected databases."""

    def __init__(self, model_wrapper, retriever=None):
        super().__init__(AgentType.TABLE_SCHEMA_RETRIEVER, model_wrapper)
        self._retriever = retriever
    
    def process(self, state: AgentState) -> AgentResult:
        """Identify relevant tables from the selected databases."""
        logger.info(f"🔍 {self.name}: Identifying relevant tables from databases")

        try:
            # Validate prerequisites and get available tables
            validation_error = AgentUtils.validate_state_prerequisites(state, ["relevant_databases"])
            if validation_error:
                return validation_error

            # Store selected databases for use in semantic search
            self._selected_databases = state.relevant_databases

            # Generate structured table selection response
            system_message = self._create_table_identification_system_prompt(state)
            human_message = state.natural_language_query

            table_selection = self.generate_with_llm(
                schema_class=TableSelection,
                system_message=system_message,
                human_message=human_message,
                temperature=0
            )

            # Extract table names from the structured response
            table_names = table_selection.table_names
            logger.info(f"🔍 Identified tables: {table_names}")

            return self._create_success_result(table_names)

        except Exception as e:
            logger.error(f"❌ Table identification failed: {e}")
            return AgentUtils.create_error_result(str(e))


    def _create_success_result(self, table_names: List[str]) -> AgentResult:
        """Create success result with identified tables."""

        state_updates = {
            "relevant_tables": table_names,
            "current_step": "tables_identified"
        }

        return AgentResult(
            success=True,
            message="Tables identified successfully",
            state_updates=state_updates
        )
    
    def _create_table_identification_system_prompt(self, state: AgentState) -> str:
        """Create system prompt for table identification."""
        feedback_section = AgentUtils.get_validation_feedback_section(state)
        human_feedback_section = AgentUtils.build_human_feedback_section(state, "tables")

        # Try to retrieve and format relevant table chunks
        tables_section = self._retrieve_table_chunks(state.natural_language_query, n_results=15)
        logger.info(f"🔍 Tables section: {tables_section}")

        # Use fallback if no chunks found
        if not tables_section:
            tables_section = "**Available Tables:**\n(None found - retriever unavailable)"

        prompt_parts = [
            "You are an expert table selector agent. Your task is to identify ALL relevant tables needed to answer the user's question from the available database tables."
        ]

        if feedback_section:
            prompt_parts.append(feedback_section)
        if human_feedback_section:
            prompt_parts.append(human_feedback_section)
        if tables_section:
            prompt_parts.append(tables_section)

        prompt_parts.append("""**CRITICAL INSTRUCTIONS:**
1. **MANDATORY: Include core entity tables** for user/customer/account queries:
   - ALWAYS include: "customers", "users", "accounts" tables when mentioned or implied
   - These foundational tables are CRITICAL for proper identification

2. **Analyze the query requirements carefully:**
   - What entities are mentioned? (customers, users, accounts, transactions, wallet_events, etc.)
   - What specific data is needed? (dates, statuses, amounts, verification info, transaction details, etc.)
   - What filters/conditions? (date ranges, status checks, amount thresholds, etc.)
   - What relationships need to be joined? (customer to transactions, accounts to wallet_events, etc.)

3. **Leverage the detailed table information provided:**
   - **Column Structure:** Review the column names, data types, and constraints (PRIMARY KEY, UNIQUE, INDEX, NOT NULL)
   - **Key Relationships:** Primary keys indicate unique identifiers, foreign key relationships suggest JOIN requirements
   - **Indexed Columns:** These are optimized for filtering and should be considered for performance-critical queries
   - **Table Purpose:** Understanding what each table stores helps determine relevance

4. **Table Selection Rules:**
   - **CRITICAL:** You MUST ONLY select tables from the available tables list provided above
   - **STRICTLY FORBIDDEN:** Do not include any tables that are not explicitly listed in the available tables section
   - **MANDATORY:** If user-suggested tables are provided, they MUST be included in your selection ONLY if they appear in the available tables list above
   - Select ALL tables that contain relevant data for the complete query execution (from the provided list only)
   - Use exact table names from the available tables list above (format: database.table_name)
   - Include relationship tables needed for JOINs between selected tables (only if they exist in the provided list)
   - Consider tables with relevant indexed columns for query performance (only from the provided list)
   - Include lookup/reference tables that provide context for the main entities (only from the provided list)
   - **ABSOLUTE REQUIREMENT:** If a table you need is not in the available list, you cannot select it - work with what's available

5. **Query Complexity Considerations:**
   - For simple lookups: Include base entity tables + any directly related tables
   - For analytical queries: Include transaction/event tables + dimension tables for filtering
   - For reporting queries: Include all tables needed for aggregations and groupings
   - For time-based queries: Ensure date/timestamp columns are available in selected tables

**CRITICAL: Response Format Requirements:**
- Return ONLY the JSON data object, NOT the schema definition
- Your response must be valid JSON that matches this exact structure:
  ```json
  {{
    "reasoning": "Your detailed explanation here",
    "table_names": ["database.table1", "database.table2", "database.table3"]
  }}
  ```
- Do NOT include any schema definitions, descriptions, or metadata
- Do NOT wrap your response in markdown code blocks
- The response must be parseable JSON that directly matches the required fields""")

        return "\n\n".join(prompt_parts)
    

    def _retrieve_table_chunks(self, query: str, n_results: int = 25) -> str:
        """Retrieve relevant table chunks and format them for the prompt."""
        if not self._retriever:
            return ""

        selected_databases = getattr(self, '_selected_databases', [])
        if not selected_databases:
            logger.warning("⚠️ No selected databases available")
            return ""

        try:
            results = self._retriever.search_tables_in_databases(query, selected_databases, n_results=max(n_results, 25))
            chunk_count = len(results.get('documents', [[]])[0]) if results.get('documents') else 0
            logger.info(f"🔍 Found {chunk_count} table chunks in databases {selected_databases}")

            formatted_content = ChunkParsers.format_table_chunks_filtered_by_databases(results, selected_databases)
            if formatted_content and formatted_content != "**Available Tables:**\n(None found)":
                logger.info(f"🔍 Formatted table chunks: {len(formatted_content)} characters")
                return formatted_content
            else:
                return ""

        except Exception as e:
            logger.error(f"❌ Error retrieving chunks: {e}")
            return ""
