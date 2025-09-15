"""
Query Planner Agent for the refined text2query system.

Creates a logical, step-by-step plan in natural language for how to answer the user's question.
This is a crucial reasoning step that happens before any SQL is written.
"""

import logging
from typing import List

from lang2query.utils.logging import log_ai_response

from .base_agent import BaseAgent
from .models import AgentResult, AgentState, AgentType

logger = logging.getLogger(__name__)


class QueryPlannerAgent(BaseAgent):
    """Agent responsible for creating a logical query plan."""

    def __init__(self, model_wrapper):
        super().__init__(AgentType.QUERY_PLANNER, model_wrapper)

    def process(self, state: AgentState) -> AgentResult:
        """
        Create a step-by-step query plan based on the question and schema.

        Args:
            state: Current agent state with natural language query and relevant schema

        Returns:
            AgentResult with query plan
        """
        logger.info(f"🧠 {self.name}: Creating query plan")

        try:
            # Build detailed schema information for better planning
            from lang2query.config import DOCS_DIR
            from lang2query.utils.chunks_loader import ChunksLoader

            loader = ChunksLoader(str(DOCS_DIR))
            loader.load()

            # Get detailed schema for selected tables and columns
            schema_info = self._build_detailed_schema(
                loader,
                state.relevant_databases,
                state.relevant_tables,
                state.relevant_columns,
            )

            # Generate query plan prompt with detailed schema
            prompt = self._create_planning_prompt(
                state,
                state.relevant_databases,
                state.relevant_tables,
                state.relevant_columns,
                schema_info,
            )

            query_plan = self.generate_with_llm(
                prompt,
                max_new_tokens=128,
                temperature=0.4,
                top_p=0.9,
                repetition_penalty=1.15,
            )
            log_ai_response(logger, "Query Planner", query_plan)

            # Update state with query plan
            state_updates = {"query_plan": query_plan, "current_step": "query_planned"}

            logger.info("✅ Query planning completed successfully")
            logger.info(f"📝 Plan: {query_plan}")

            return AgentResult(
                success=True,
                message="Query plan created successfully",
                state_updates=state_updates,
            )

        except Exception as e:
            logger.error(f"❌ Query planning failed: {e}")
            return AgentResult(
                success=False, message=f"Query planning failed: {str(e)}"
            )

    def _create_planning_prompt(
        self,
        state: AgentState,
        database_names: List[str],
        tables: List[str],
        columns: List[str],
        schema_info: str,
    ) -> str:
        """Create a more robust prompt for query planning.

        If available, includes prior validation feedback (rejection reason) to guide retries.
        """
        query = state.natural_language_query

        few_shot_example = """
        {
        "schema_assessment": "The provided schema seems sufficient. It contains tables for customers, their accounts, and transactions. The link between them appears to be direct.",
        "plan": [
            "1. Identify the target customer by filtering the 'customers' table for 'customer_id' = 501.",
            "2. Find all accounts associated with this customer by joining 'customers' with the 'accounts' table on 'customers.customer_id' = 'accounts.customer_id'.",
            "3. Find all card transactions associated with these accounts by joining the result with the 'card_transactions' table on 'accounts.account_id' = 'card_transactions.account_id'.",
            "4. Find all standard debit transactions by joining the result with the 'standard_transactions' table on 'accounts.account_id' = 'standard_transactions.account_id'.",
            "5. Filter both transaction sets for debit transactions in the year 2024.",
            "6. Combine the results of the two transaction types.",
            "7. Order the combined transactions by the debit amount in descending order and select the top 3.",
            "8. Select the final columns: transaction amount and transaction source."
        ]
        }
        """

        # Optional prior feedback context from validator
        feedback = state.query_validation_feedback or {}
        prior_feedback_section = ""
        if not feedback.get("overall_valid", True):
            reason = feedback.get("reason") or feedback.get("llm_judgment")
            if reason:
                prior_feedback_section = f"""
        \nContext From Previous Validation (use to improve the plan):\n
        The last generated query was judged INVALID because: "{reason}".\n
        Address this when constructing the plan.\n
        """

        return f"""
        You are a meticulous Principal Data Architect. Your task is to create a detailed, step-by-step query plan based on a user's question and a database schema. You must also critically assess if the provided schema is sufficient to answer the question.

        **User Question:** "{query}"

        **Selected Schema Information:**
        Databases: {", ".join(database_names)}
        Tables: {", ".join(tables)}
        Columns: {", ".join(columns)}

        {prior_feedback_section}

        **Detailed Database Schema:**
        ```sql
        {schema_info}
        ```

        The above schema information is selected by previous agents according to user question and available schema.

        **Instructions:**
        1.  **Schema Assessment:** First, in the `schema_assessment` field, critically evaluate the provided schema. State whether it appears complete for this query. If you suspect a table or a key relationship is missing, describe what is needed (e.g., "A linking table between 'users' and 'products' seems to be missing.").
        2.  **Execution Plan:** In the `plan` field, provide a numbered, step-by-step natural language plan.
        3.  **Be Explicit:** Clearly state every table, filter, and aggregation.
        4.  **Full Join Path:** For joins, describe the complete path, mentioning every table and the keys to join on (e.g., "Join 'table_A' to 'table_B' on A.id = B.a_id, then join the result to 'table_C' on B.id = C.b_id").
        5.  **Final Output:** Your response MUST be a single, valid JSON object containing the `schema_assessment` and the `plan`. Do not add any text before or after the JSON object.

        **Example Output:**
        ```json
        {few_shot_example}
        ```

        **JSON Output:**
        """

    def _build_detailed_schema(
        self,
        loader,
        database_names: List[str],
        table_names: List[str],
        column_names: List[str] = None,
    ) -> str:
        """Build detailed schema information for ONLY the selected databases, tables, and columns."""
        schema_lines = []

        if not table_names:
            logger.warning("⚠️ No table names provided, cannot build schema")
            return "-- No tables selected for schema generation"

        for db_name in database_names:
            db = loader.databases.get(db_name)
            if not db:
                continue

            # Only include tables that were identified by previous agents
            relevant_tables = [t for t in db.tables.values() if t.name in table_names]

            if not relevant_tables:
                logger.debug(f"No relevant tables found in database {db_name}")
                continue

            schema_lines.append(f"-- Database: {db_name}")
            if db.purpose:
                schema_lines.append(f"-- Purpose: {db.purpose}")
            schema_lines.append("")

            for table in relevant_tables:
                schema_lines.append(f"CREATE TABLE {table.name} (")

                if table.columns:
                    column_defs = []
                    for col in table.columns:
                        # Only include columns that were identified by previous agents (if column filtering is enabled)
                        if column_names and col.name not in column_names:
                            continue

                        col_def = f"    {col.name}"
                        if col.data_type:
                            col_def += f" {col.data_type}"
                        if col.is_primary_key:
                            col_def += " PRIMARY KEY"
                        if col.is_unique:
                            col_def += " UNIQUE"
                        # Note: nullable information not available in current schema
                        column_defs.append(col_def)

                    if column_defs:
                        schema_lines.append(",\n".join(column_defs))
                    else:
                        schema_lines.append("    -- No relevant columns found")
                else:
                    schema_lines.append("    -- No column information available")

                schema_lines.append(");")
                if table.purpose:
                    schema_lines.append(f"-- Purpose: {table.purpose}")
                schema_lines.append("")

        if not schema_lines:
            logger.warning(
                "⚠️ No schema information could be built from selected tables"
            )
            return "-- No schema information available for selected tables"

        return "\n".join(schema_lines)
