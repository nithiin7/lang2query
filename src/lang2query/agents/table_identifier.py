"""
Table Identifier Agent for the Lang2Query system.

Uses chunks_loader to identify relevant tables from the databases selected
by the previous database_identifier agent.
"""

import json
import logging
from typing import Dict, List

from lang2query.config import DOCS_DIR
from lang2query.utils.chunks_loader import ChunksLoader
from lang2query.utils.logging import log_ai_response

from .base_agent import BaseAgent
from .models import AgentResult, AgentState, AgentType

logger = logging.getLogger(__name__)


class TableIdentifier(BaseAgent):
    """Agent responsible for identifying relevant tables from selected databases."""

    def __init__(self, model_wrapper):
        super().__init__(AgentType.TABLE_SCHEMA_RETRIEVER, model_wrapper)
        # Load chunks for table information
        loader = ChunksLoader(str(DOCS_DIR))
        loader.load()
        self._chunks_loader = loader

    def process(self, state: AgentState) -> AgentResult:
        """
        Identify relevant tables from the selected databases.

        Args:
            state: Current agent state with relevant databases

        Returns:
            AgentResult with relevant table names and related_db mapping
        """
        logger.info(f"🔍 {self.name}: Identifying relevant tables from databases")

        try:
            # Get available tables from selected databases
            available_tables_list = self._chunks_loader.available_tables(
                state.relevant_databases
            )

            if not available_tables_list:
                logger.warning("⚠️ No tables found for selected databases")
                return AgentResult(
                    success=False, message="No tables found for selected databases"
                )

            # Convert list to formatted text for prompt
            available_tables = self._format_tables_for_prompt(available_tables_list)

            logger.info(f"🗄️ Identified tables: {available_tables}")

            # Generate table identification prompt
            prompt = self._create_table_identification_prompt(state, available_tables)

            # Get table identification from LLM
            response = self.generate_with_llm(
                prompt, max_new_tokens=64, do_sample=False
            )
            log_ai_response(logger, "Table Identifier", response)

            # Parse the response to extract table names
            table_names = self._parse_table_names(response)
            logger.info(f"🔍 Table names: {table_names}")

            # Create related_db mapping (table -> database)
            related_db = self._create_related_db_mapping(
                table_names, state.relevant_databases
            )
            logger.info(f"🔍 Related DB mapping: {related_db}")

            # Update state with identified tables
            state_updates = {
                "relevant_tables": table_names,
                "tables_retrieved": True,
                "current_step": "tables_identified",
                "related_db": related_db,
            }
            logger.info("✅ Table identification completed successfully")

            return AgentResult(
                success=True,
                message="Tables identified successfully",
                state_updates=state_updates,
            )

        except Exception as e:
            logger.error(f"❌ Table identification failed: {e}")
            return AgentResult(
                success=False, message=f"Table identification failed: {str(e)}"
            )

    def _create_table_identification_prompt(
        self, state: AgentState, available_tables: str
    ) -> str:
        """Create prompt for table identification.

        If available, includes prior validation feedback (rejection reason) to guide retries.
        """
        query = state.natural_language_query

        few_shot_example = """
        {
        "reasoning": "The query asks for customer information with KYC status. I need tables that contain customer data and KYC information. The 'customers' table has customer details, and 'kyc_verification' table has KYC status information. Both are needed to answer the query completely.",
        "table_names": ["customers", "kyc_verification"]
        }
        """

        # Optional prior feedback context from validator
        feedback = state.query_validation_feedback or {}
        prior_feedback_section = ""
        if not feedback.get("overall_valid", True):
            reason = feedback.get("reason") or feedback.get("llm_judgment")
            if reason:
                prior_feedback_section = f"""
                \n**Context From Previous Validation (use to improve selection):**\n
                The last generated query was judged INVALID because: "{reason}".\n
                The database is selected by the previous agent with considering this reason.\n
                Consider this when choosing tables so the next attempt fully fixes the issue.\n
                """

        return f"""
        You are a database table selection expert. Your task is to identify the most relevant table(s) needed to answer a user's query from the available tables in the selected databases.

        **User Query:**
        "{query}"

        {prior_feedback_section}

        **Available Tables:**
        {available_tables}

        **Instructions:**
        1. First, write down your step-by-step reasoning in the `reasoning` field. Analyze the user's query to determine what information is needed.
        2. Consider which tables contain the data required to answer the query.
        3. Think about potential JOINs - if the query needs data from multiple related tables, include all necessary tables.
        4. In the `table_names` field, provide a JSON list of table names that are necessary to answer the query.
        5. Only choose table names from the "Available Tables" list above. Use the exact table names as shown (e.g., "customers", "kyc_verification").
        6. If no tables contain the required information, return an empty list for `table_names` and explain why in your reasoning.
        7. Your final output must be a single, valid JSON object and nothing else.

        **Example Output Format:**
        (Few examples for your reference, these may not be related to the user query)
        ```json
        {few_shot_example}
        ```

        **JSON Output:**
        """

    def _parse_table_names(self, response: str) -> List[str]:
        """Parse table names from LLM response."""
        try:
            text = response.strip()

            # Try to extract JSON from response
            try:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = text[json_start:json_end]
                    obj = json.loads(json_text)
                    candidates = obj.get("table_names", [])
                else:
                    candidates = []
            except Exception:
                candidates = []

            # If JSON parsing failed, try to extract table names from text
            if not candidates:
                # Look for table names in backticks or quotes
                import re

                table_pattern = r"`([a-zA-Z_][a-zA-Z0-9_]*)`"
                candidates = re.findall(table_pattern, text)

                # Also look for quoted table names
                if not candidates:
                    quoted_pattern = r'"([a-zA-Z_][a-zA-Z0-9_]*)"'
                    candidates = re.findall(quoted_pattern, text)

            # Validate table names against available tables and get original case
            valid_tables = []
            for table_name in candidates:
                table_name = str(table_name).strip()
                if table_name:
                    # Find the original case version of the table name
                    original_table_name = self._get_original_table_name(table_name)
                    if original_table_name:
                        valid_tables.append(original_table_name)

            # Remove duplicates while preserving order
            seen = set()
            unique_tables = []
            for table in valid_tables:
                if table not in seen:
                    seen.add(table)
                    unique_tables.append(table)

            if not unique_tables:
                logger.warning("⚠️ No valid tables identified from response")
                return []

            return unique_tables[:5]  # Limit to 5 tables max

        except Exception as e:
            logger.error(f"❌ Failed to parse table names: {e}")
            return []

    def _is_valid_table_name(self, table_name: str) -> bool:
        """Check if table name exists in any of the loaded databases (case-insensitive)."""
        table_name_lower = table_name.lower()
        for db_name, db_schema in self._chunks_loader.databases.items():
            for existing_table_name in db_schema.tables.keys():
                if existing_table_name.lower() == table_name_lower:
                    return True
        return False

    def _get_original_table_name(self, table_name: str) -> str:
        """Get the original case version of a table name from the loaded databases."""
        table_name_lower = table_name.lower()
        for db_name, db_schema in self._chunks_loader.databases.items():
            for existing_table_name in db_schema.tables.keys():
                if existing_table_name.lower() == table_name_lower:
                    return existing_table_name
        return None

    def _format_tables_for_prompt(self, tables_list: List[Dict[str, str]]) -> str:
        """Convert list of table info dictionaries to formatted text for prompt."""
        lines = []
        for table_info in tables_list:
            name = table_info["name"]
            desc = table_info["description"]
            database = table_info["database"]

            lines.append(f"- `{name}` (from {database}): {desc}")
        return "\n".join(lines)

    def _create_related_db_mapping(
        self, table_names: List[str], database_names: List[str]
    ) -> Dict[str, str]:
        """Create mapping of table names to their database names."""
        related_db = {}

        for table_name in table_names:
            for db_name in database_names:
                db_schema = self._chunks_loader.databases.get(db_name)
                if db_schema:
                    # Check for table with case-insensitive matching
                    for existing_table_name in db_schema.tables.keys():
                        if existing_table_name.lower() == table_name.lower():
                            related_db[table_name] = db_name
                            break
                    if table_name in related_db:
                        break

        return related_db
