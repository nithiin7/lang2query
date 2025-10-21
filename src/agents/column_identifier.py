"""
Column Identifier Agent for the refined text2query system.

Identifies relevant columns from the previously identified tables. Mirrors
the output style of TableIdentifier and provides data for downstream agents.
"""

import logging
from typing import List, Dict, Any
from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from utils import ChunkParsers
from models.models import AgentState, AgentResult, AgentType, ColumnSelection


logger = logging.getLogger(__name__)


class ColumnIdentifier(BaseAgent):
    """Agent responsible for identifying relevant columns for the query."""

    def __init__(self, model_wrapper, retriever=None):
        super().__init__(AgentType.COLUMN_IDENTIFIER, model_wrapper)
        self._retriever = retriever


    def process(self, state: AgentState) -> AgentResult:
        """Identify relevant columns from previously identified tables."""
        logger.info(f"🧩 {self.name}: Identifying relevant columns from tables")

        try:
            # Validate prerequisites
            validation_error = AgentUtils.validate_state_prerequisites(state, ["relevant_tables"])
            if validation_error:
                return validation_error

            # Get column details and generate system prompt
            table_columns = self._get_table_columns(state)
            system_message = self._create_column_identification_system_prompt(state, table_columns)
            human_message = state.natural_language_query

            # Generate structured column selection response
            column_selection = self.generate_with_llm(
                schema_class=ColumnSelection,
                system_message=system_message,
                human_message=human_message,
                temperature=0.1
            )

            # Extract selected columns from the structured response
            selected_columns = self._extract_columns_from_selection(column_selection)
            logger.info(f"🧩 Selected columns: {selected_columns}")

            # If no columns were found
            if not selected_columns:
                logger.warning("🧩 No columns selected - query may not be answerable with current schema")

            # Return success result
            return self._create_success_result(selected_columns)

        except Exception as e:
            logger.error(f"❌ Column identifier failed: {e}")
            return AgentUtils.create_error_result(str(e))

    def _get_table_columns(self, state: AgentState) -> Dict[str, List[Dict[str, Any]]]:
        """Get column details for selected tables using retriever."""
        if not self._retriever:
            logger.warning("🧩 Retriever not available, returning empty column details")
            return {}

        table_columns = {}

        # Group tables by database
        tables_by_db = self._group_tables_by_database(state.relevant_tables)

        # For each database, get columns for the relevant tables
        for db_name, table_names in tables_by_db.items():
            try:
                db_table_columns = self._retriever.get_columns_by_table(
                    db_name, table_names
                )
                table_columns.update(db_table_columns)
            except Exception as e:
                logger.error(f"🧩 Failed to get columns for database {db_name}: {e}")

        logger.info(f"🧩 Retrieved column details for {len(table_columns)} tables")
        return table_columns

    def _group_tables_by_database(self, table_names: List[str]) -> Dict[str, List[str]]:
        """Group table names by database. Handles both 'database.table' and 'table' formats."""
        tables_by_db = {}

        for table_name in table_names:
            if '.' in table_name:
                # Format: database.table
                db_name, table_name_only = table_name.split('.', 1)
            else:
                # Format: table (no database prefix) - use 'default' as database name
                db_name = 'default'
                table_name_only = table_name

            if db_name not in tables_by_db:
                tables_by_db[db_name] = []
            tables_by_db[db_name].append(table_name_only)

        return tables_by_db

    def _create_success_result(self, selected_columns: List[str]) -> AgentResult:
        """Create success result with state updates."""
        state_updates = {
            "relevant_columns": selected_columns,
            "current_step": "columns_identified"
        }

        return AgentResult(
            success=True,
            message="Columns identified successfully",
            state_updates=state_updates
        )

    def _extract_columns_from_selection(self, column_selection: ColumnSelection) -> List[str]:
        """Extract column names from the structured ColumnSelection response."""
        selected_columns = []

        for table_name, table_columns in column_selection.columns.items():
            for column_name in table_columns.keys():
                if column_name and column_name.strip():
                    selected_columns.append(column_name.strip())

        return AgentUtils.normalize_list_items(selected_columns)


    def _create_column_identification_system_prompt(self, state: AgentState, table_columns: Dict[str, List[Dict[str, Any]]]) -> str:
        """Create system prompt to choose relevant columns from the given tables."""
        columns_section = ChunkParsers.format_column_details(table_columns)
        feedback_section = AgentUtils.get_validation_feedback_section(state)

        return f"""You are an expert SQL column selector specializing in precise schema analysis. Your task is to identify the MINIMUM set of columns needed to construct an efficient, complete SQL query that answers the user's question.

{feedback_section}

{columns_section}

**Critical Column Selection Guidelines:**

1. **ALWAYS include identifier columns for JOINs**: Select PRIMARY KEY and UNIQUE columns that will be used to connect tables
2. **Include columns directly referenced in the query**: Select columns mentioned in WHERE, HAVING, ORDER BY clauses
3. **Include columns needed for the result**: Select columns that should appear in SELECT clause or are needed for aggregations
4. **Include columns for filtering and grouping**: Select columns used in GROUP BY, date ranges, status filters, etc.
5. **Consider data types and constraints**: Choose appropriate data types (dates for date filters, numeric for counts, etc.)

**Leverage the Detailed Column Information Provided:**
- **PRIMARY KEY columns**: Essential for JOINs and unique identification
- **UNIQUE columns**: Useful for filtering and ensuring data integrity
- **INDEXED columns**: Optimized for filtering and sorting - prefer these for WHERE conditions
- **Data Types**: Match column types to query requirements (timestamp for dates, decimal for amounts, etc.)
- **Nullability**: Consider whether columns can be NULL when designing filters
- **Descriptions**: Use column descriptions to understand the business meaning

**Systematic Analysis Process:**
1. **Break down the query**: Identify what data is being requested (counts, lists, specific values, etc.)
2. **Identify filtering criteria**: What conditions, dates, statuses, or categories are mentioned?
3. **Determine JOIN requirements**: Which PRIMARY KEY/UNIQUE columns are needed to connect the selected tables?
4. **Select result columns**: What columns should appear in the final output?
5. **Optimize for performance**: Prioritize INDEXED columns for filtering, choose minimal required set

**Column Selection Strategy:**
- **JOIN Keys**: Always include PRIMARY KEY columns from tables being joined
- **Filter Columns**: Prefer INDEXED columns for WHERE conditions when available
- **Result Columns**: Only include columns that will appear in SELECT or are needed for aggregations
- **Date/Time Columns**: Use timestamp/datetime columns for date filtering
- **Status/Flag Columns**: Use appropriate columns for status checks and categorizations
- **Amount/Value Columns**: Use decimal/numeric columns for financial calculations

**Instructions:**
1. Analyze the query systematically using the process above
2. Review the detailed column information to understand constraints and data types
3. For each selected table, choose ONLY the columns that are absolutely necessary
4. Prioritize INDEXED columns for filtering operations
5. Include PRIMARY KEY columns for any table that will participate in JOINs
6. Consider data types to ensure proper query construction
7. Do not select columns that are not needed for the specific query requirements

**Example Analysis:**
For query "Count customers who joined in 2023":
- customers table: customer_id [PRIMARY KEY] (JOIN key), created_date (filter), status (active check)
- orders table: customer_id [INDEXED] (JOIN key), order_date (additional date filter)

**Requirements:**
1. **If no columns are needed**, provide reasoning explaining why no columns are selected
2. **Only include columns that exist** in the tables listed above
3. **Each column must have a specific purpose** in answering the query
4. **Reference column constraints** (PRIMARY KEY, INDEXED, etc.) in your reasoning
5. **Provide clear reasoning** for your column selection decisions

**CRITICAL: Response Format Requirements:**
- Return ONLY the JSON data object, NOT the schema definition
- Your response must be valid JSON that matches this exact structure:
  ```json
  {{
    "reasoning": "Your detailed explanation here",
    "columns": {{
      "table_name": {{
        "column_name": "reason for selection"
      }}
    }}
  }}
  ```
- Do NOT include any schema definitions, descriptions, or metadata
- Do NOT wrap your response in markdown code blocks
- The response must be parseable JSON that directly matches the required fields
"""