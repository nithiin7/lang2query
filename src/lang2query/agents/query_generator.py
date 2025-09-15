"""
Query Generator Agent for the refined text2query system.

Generates queries from the query plan and schema information.
This is a much simpler task than going from natural language directly to query.
"""

import logging
from typing import List

from lang2query.utils.logging import log_ai_response

from .base_agent import BaseAgent
from .models import AgentResult, AgentState, AgentType, Query

logger = logging.getLogger(__name__)


class QueryGeneratorAgent(BaseAgent):
    """
    Agent that generates queries from query plan and schema.

    Takes the clear, step-by-step plan and translates it into valid query.
    """

    def __init__(self, model):
        """Initialize the Query Generator Agent."""
        super().__init__(AgentType.QUERY_GENERATOR, model)
        logger.info("🔧 Query Generator Agent initialized")

    def process(self, state: AgentState) -> AgentResult:
        """
        Generate query from query plan and schema.

        Args:
            state: Current agent state with query plan and schema

        Returns:
            AgentResult with generated query
        """
        try:
            logger.info("🔨 Generating query from query plan...")

            if not state.query_plan:
                logger.error("❌ No query plan available for query generation")
                return AgentResult(
                    success=False,
                    message="No query plan available for query generation",
                )

            if not state.relevant_databases:
                logger.error("❌ No schema available for query generation")
                return AgentResult(
                    success=False, message="No databases available for query generation"
                )

            if not state.relevant_tables:
                logger.error("❌ No tables available for query generation")
                return AgentResult(
                    success=False, message="No tables available for query generation"
                )

            if not state.relevant_columns:
                logger.error("❌ No columns available for query generation")
                return AgentResult(
                    success=False, message="No columns available for query generation"
                )

            # Generate detailed schema information from chunks loader
            from lang2query.config import DOCS_DIR
            from lang2query.utils.chunks_loader import ChunksLoader

            loader = ChunksLoader(str(DOCS_DIR))
            loader.load()

            # Get detailed schema for selected tables and columns only
            schema_info = self._build_detailed_schema(
                loader,
                state.relevant_databases,
                state.relevant_tables,
                state.relevant_columns,
            )
            logger.info(f"🔍 Schema info: {schema_info}")

            query = self._generate_query_from_plan(
                state,
                state.query_plan,
                schema=schema_info,
                database_names=state.relevant_databases or [],
            )
            logger.info(f"✅ Generated query: {query.query}")

            if not query:
                logger.error("❌ Failed to generate query")
                return AgentResult(success=False, message="Failed to generate query")

            logger.info(f"📊 Query confidence: {query.confidence_score:.2f}")

            return AgentResult(
                success=True,
                message="Successfully generated query",
                state_updates={
                    "generated_query": query,
                    "current_step": "query_generated",
                },
            )

        except Exception as e:
            logger.error(f"❌ Query generation failed: {e}")
            return AgentResult(
                success=False, message=f"Query generation error: {str(e)}"
            )

    def _generate_query_from_plan(
        self,
        state: AgentState,
        query_plan: str,
        schema: str,
        database_names: List[str] = None,
    ) -> Query:
        """
        Generate query from query plan and schema.

        Args:
            query_plan: Step-by-step natural language plan
            schema: Database schema information

        Returns:
            Query object with generated query
        """
        try:
            # Create prompt for query generation from plan
            prompt = self._create_query_from_plan_prompt(
                state,
                query_plan,
                schema,
                database_names=database_names or [],
            )
            logger.debug("🤖 Generating query from plan with LLM...")

            response = self.generate_with_llm(
                prompt, max_new_tokens=128, do_sample=False
            )
            log_ai_response(logger, "Query Generator", response)

            if not response or not response.strip():
                logger.warning("⚠️ Empty response from model, creating fallback query")
                return self._create_fallback_query_from_plan(query_plan, schema)

            # Parse query from response
            logger.debug("🔍 Extracting query from LLM response...")
            query_text = self._extract_query_from_response(response)

            if not query_text:
                logger.warning(
                    "⚠️ Could not extract query from response, creating fallback"
                )
                return self._create_fallback_query_from_plan(query_plan, schema)

            # Create Query object
            return Query(
                query=query_text,
                database="unknown",
                tables_used=self._extract_tables_from_query(query_text),
                columns_used=self._extract_columns_from_query(query_text),
                confidence_score=self._calculate_plan_confidence(
                    query_plan, query_text
                ),
                explanation=f"Generated from plan: {query_plan[:100]}...",
            )

        except Exception as e:
            logger.error(f"❌ Query generation from plan failed: {e}")
            return self._create_fallback_query_from_plan(query_plan, schema)

    def _create_query_from_plan_prompt(
        self,
        state: AgentState,
        query_plan: str,
        schema: str,
        dialect: str = "SQL",
        database_names: List[str] = None,
    ) -> str:
        """Create a robust prompt for query generation from a query plan.

        If available, includes prior validation feedback (rejection reason) to guide retries.
        """

        # This example demonstrates the expected quality: aliases, qualified columns, etc.
        few_shot_example = """
        -- This is an example of a high-quality query.
        SELECT
        c.customer_name,
        COUNT(o.order_id) AS total_orders,
        SUM(p.price * oi.quantity) AS total_spent
        FROM customers AS c
        JOIN orders AS o
        ON c.customer_id = o.customer_id
        JOIN order_items AS oi
        ON o.order_id = oi.order_id
        JOIN products AS p
        ON oi.product_id = p.product_id
        WHERE
        c.signup_date >= '2023-01-01'
        GROUP BY
        c.customer_name
        ORDER BY
        total_spent DESC;
        """

        dbs = ", ".join(database_names or [])

        # Optional prior feedback context from validator
        feedback = state.query_validation_feedback or {}
        prior_feedback_section = ""
        if not feedback.get("overall_valid", True):
            reason = feedback.get("reason") or feedback.get("llm_judgment")
            if reason:
                prior_feedback_section = f"""
        \nContext From Previous Validation (fix in this query):\n
        The last generated query was judged INVALID because: "{reason}".\n
        Ensure this query addresses the noted issue fully.\n
        """

        return f"""
        You are a Senior Database Engineer who writes clean, efficient, and dialect-specific SQL.
        Your task is to convert a query plan into a single, syntactically perfect SQL query.

        **Query Plan:**
        {query_plan}

        **Databases:** {dbs}

        {prior_feedback_section}

        **Database Schema:**
        ```sql
        {schema}
        ```

        **Target Dialect:** {dialect}

        **CRITICAL Instructions:**
        1.  Translate the plan into a single, valid {dialect} query compliant with the **{dialect}** dialect.
        2.  **Use table aliases** for every table involved (e.g., `FROM customers AS c`).
        3.  **Qualify ALL column names** with their corresponding table alias (e.g., `c.customer_id`) if the query is complex.
        4.  Follow the join logic, filters, and aggregations from the plan precisely. Use joins only if required. Do not use Join for straightforward queries.
        5.  Do not add any comments or explanations outside of the {dialect} query itself.
        6.  Your final output must be ONLY the raw {dialect} query.
        7.  Do not use any other tables or columns which are not defined in the schema.
        8.  You cannot create new tables or columns.

        **Example of Expected Quality and Style:**
        ```sql
        {few_shot_example}
        ```

        **SQL Query:**
        """

    def _extract_query_from_response(self, response: str) -> str:
        """Extract the first valid query from LLM response."""
        try:
            # Split response by semicolons to get individual queries
            potential_queries = response.split(";")

            for query_part in potential_queries:
                query_part = query_part.strip()

                # Skip empty parts
                if not query_part:
                    continue

                # Remove markdown code blocks if present
                lines = query_part.split("\n")
                in_code_block = False
                clean_lines = []

                for line in lines:
                    if line.strip().startswith("```"):
                        in_code_block = not in_code_block
                        continue

                    if in_code_block or not line.strip().startswith("```"):
                        # Skip empty lines and comments
                        if line.strip() and not line.strip().startswith("--"):
                            clean_lines.append(line.strip())

                query = "\n".join(clean_lines).strip()

                if "SELECT" in query.upper():
                    # Clean up the query
                    query = self._clean_query(query)
                    logger.info(f"✅ Extracted clean query: {query[:100]}...")
                    return query

            logger.warning("⚠️ No valid query found in response")
            return ""

        except Exception as e:
            logger.error(f"❌ Failed to extract query from response: {e}")
            return ""

    def _clean_query(self, query: str) -> str:
        """Clean and format the query."""
        try:
            # Remove extra whitespace and normalize
            lines = [line.strip() for line in query.split("\n") if line.strip()]

            # Join lines with proper spacing
            cleaned_query = "\n".join(lines)

            # Ensure query ends with semicolon
            if not cleaned_query.endswith(";"):
                cleaned_query += ";"

            return cleaned_query

        except Exception as e:
            logger.error(f"❌ Failed to clean query: {e}")
            return query

    def _create_fallback_query_from_plan(self, query_plan: str, schema: str) -> Query:
        """Create a simple fallback query when LLM generation fails."""
        logger.info("🔄 Creating fallback query from plan")

        try:
            # Try to extract table names from schema
            import re

            table_matches = re.findall(r"(\w+)\s*\(", schema)
            if table_matches:
                table_name = table_matches[0]
                return Query(
                    query=f"SELECT * FROM {table_name} LIMIT 10",
                    database="unknown",
                    tables_used=[table_name],
                    columns_used=[],
                    confidence_score=0.2,
                    explanation=f"Fallback query from plan: {query_plan[:100]}...",
                )

            # Return minimal query if no tables found
            return Query(
                query="SELECT 1",
                database="unknown",
                tables_used=[],
                columns_used=[],
                confidence_score=0.1,
                explanation="Minimal fallback query",
            )

        except Exception as e:
            logger.error(f"❌ Failed to create fallback query: {e}")
            return Query(
                query="SELECT 1",
                database="unknown",
                tables_used=[],
                columns_used=[],
                confidence_score=0.1,
                explanation="Minimal fallback query",
            )

    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Extract table names from query."""
        import re

        # Simple regex to find table names after FROM and JOIN
        table_pattern = r"(?:FROM|JOIN)\s+(\w+)"
        tables = re.findall(table_pattern, query, re.IGNORECASE)
        return list(set(tables))  # Remove duplicates

    def _extract_columns_from_query(self, query: str) -> List[str]:
        """Extract column names from query."""
        import re

        # Simple regex to find column names in SELECT
        column_pattern = r"SELECT\s+(.*?)\s+FROM"
        match = re.search(column_pattern, query, re.IGNORECASE | re.DOTALL)
        if match:
            columns_text = match.group(1)
            # Split by comma and clean up
            columns = [col.strip().split()[0] for col in columns_text.split(",")]
            return [col for col in columns if col and col != "*"]
        return []

    def _calculate_plan_confidence(self, query_plan: str, query: str) -> float:
        """Calculate confidence score for query generated from plan."""
        confidence = 0.6  # Base confidence for plan-based generation

        # Check query structure
        query_upper = query.upper()
        if "SELECT" in query_upper and "FROM" in query_upper:
            confidence += 0.2

        # Bonus for complex queries
        if any(
            keyword in query_upper
            for keyword in ["JOIN", "GROUP BY", "ORDER BY", "WHERE"]
        ):
            confidence += 0.1

        # Check if plan mentions specific operations that are in the query
        plan_lower = query_plan.lower()
        if "join" in plan_lower and "JOIN" in query_upper:
            confidence += 0.1
        if "filter" in plan_lower and "WHERE" in query_upper:
            confidence += 0.1
        if "sum" in plan_lower or "count" in plan_lower:
            if "SUM" in query_upper or "COUNT" in query_upper:
                confidence += 0.1

        return min(1.0, confidence)

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
