"""
Query Generator Agent for the refined text2query system.

Generates queries from the query plan and schema information.
This is a much simpler task than going from natural language directly to query.
"""

import logging
from typing import List

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from models.models import AgentState, AgentResult, AgentType, Query

logger = logging.getLogger(__name__)


class QueryGeneratorAgent(BaseAgent):
    """
    Agent that generates queries from query plan and schema.
    
    Takes the clear, step-by-step plan and translates it into valid query.
    """
    
    def __init__(self, model, retriever=None):
        """Initialize the Query Generator Agent."""
        super().__init__(AgentType.QUERY_GENERATOR, model)
        self._retriever = retriever
    
    def process(self, state: AgentState) -> AgentResult:
        """Generate query from query plan and schema."""
        logger.info("🔨 Generating query from query plan...")

        try:
            # Validate prerequisites
            field_checks = [
            ("query_plan", "No query plan available for query generation"),
            ("relevant_databases", "No databases available for query generation"),
            ("relevant_tables", "No tables available for query generation"),
            ("relevant_columns", "No columns available for query generation"),
        ]

            validation_error = AgentUtils.validate_multiple_fields(state, field_checks)
            if validation_error:
                return validation_error

            # Generate schema and query
            query = self._generate_query_from_plan(state, state.query_plan)
            if not query:
                logger.error("❌ Failed to generate query")
                return AgentResult(success=False, message="Failed to generate query")

            return self._create_success_result(query)

        except Exception as e:
            logger.error(f"❌ Query generation failed: {e}")
            return AgentUtils.create_error_result(str(e))


    def _create_success_result(self, query: Query) -> AgentResult:
        """Create success result with generated query."""
        return AgentResult(
            success=True,
            message="Successfully generated query",
            state_updates={"generated_query": query, "current_step": "query_generated"}
        )

    
    def _generate_query_from_plan(self, state: AgentState, query_plan: str) -> Query:
        """Generate query from query plan and schema."""
        try:
            system_message = self._create_query_from_plan_system_prompt(
                state, query_plan, dialect=state.dialect
            )
            human_message = state.natural_language_query

            logger.debug("🤖 Generating query from plan with LLM...")

            response = self.generate_with_llm(
                system_message=system_message,
                human_message=human_message,
                tools=[],
                temperature=0.2
            )
            query_text = self._extract_query_from_response(response)

            if not query_text:
                logger.warning("⚠️ Could not extract query from response")
                return None

            # Determine database name from available databases
            database_name = "unknown"
            if state.relevant_databases:
                if len(state.relevant_databases) == 1:
                    database_name = state.relevant_databases[0]
                else:
                    # For multiple databases, use the first one as primary
                    # The query will handle cross-database references
                    database_name = state.relevant_databases[0]
                    logger.info(f"🔗 Query spans multiple databases: {state.relevant_databases}, using {database_name} as primary")

            return Query(
                query=query_text,
                database=database_name,
                tables_used=self._extract_tables_from_query(query_text),
                columns_used=self._extract_columns_from_query(query_text),
                explanation=f"Generated from plan: {query_plan[:100]}..."
            )

        except Exception as e:
            logger.error(f"❌ Query generation from plan failed: {e}")
            return None

    
    def _create_query_from_plan_system_prompt(self, state: AgentState, query_plan: str, dialect: str = "SQL") -> str:
        """Create system prompt for query generation from a query plan."""
        feedback_section = AgentUtils.get_validation_feedback_section(state)
        schema_section = self._get_schema_section(state)

        return f"""You are a Senior Database Engineer specializing in precise query construction. Your task is to systematically translate a query plan into a single, syntactically perfect, and dialect-compliant query.

**Query Plan:**
{query_plan}

{schema_section}

{feedback_section}

**Target Dialect:** {dialect}

**SYSTEMATIC TRANSLATION PROCESS:**

1. **ANALYZE the Query Plan Structure:**
   - Identify the primary operation (SELECT, COUNT, SUM, etc.)
   - Determine query complexity (simple, aggregation, multi-table join, subquery, etc.)
   - Map plan components to SQL clauses (SELECT, FROM, WHERE, GROUP BY, ORDER BY, etc.)

2. **VALIDATE Against Schema:**
   - Verify ALL referenced tables exist in the schema
   - Confirm ALL columns are defined in their respective tables
   - Check data types match the intended operations (dates for date ranges, numeric for aggregations)
   - Ensure JOIN keys have compatible data types

3. **MAP Plan to SQL Components:**
   - Convert table references to proper FROM/JOIN clauses with aliases
   - Transform filter conditions to WHERE clauses
   - Map aggregations to appropriate GROUP BY and SELECT clauses
   - Convert sorting requirements to ORDER BY clauses

4. **APPLY Dialect-Specific Optimizations:**
   - Use {dialect}-specific functions and syntax
   - Apply appropriate indexing hints if supported
   - Use dialect-specific date/time functions
   - Optimize for {dialect} query execution patterns

**CRITICAL Query CONSTRUCTION RULES:**

**Table & Column References:**
- **ALWAYS use table aliases** for every table (e.g., `FROM users u`)
- **ALWAYS qualify column names** with aliases for multi-table queries (e.g., `u.user_id`)
- **NEVER reference tables/columns not in the schema**
- For multiple databases, in the query use <db_name>.<table_name> format

**JOIN Construction:**
- Use explicit JOIN syntax with ON clauses
- Only JOIN when plan requires relationships between tables
- Use appropriate JOIN types (INNER, LEFT, RIGHT) based on plan requirements
- Ensure JOIN conditions use correct column references with aliases

**Query Structure & Performance:**
- Place filtering conditions in WHERE clause (not ON clause when possible)
- Use appropriate aggregation functions (COUNT, SUM, AVG, etc.)
- Include GROUP BY for aggregation queries
- Add ORDER BY only when specified in plan
- Consider query performance - prefer indexed columns in WHERE clauses

**Dialect-Specific Considerations:**
- Use {dialect} date functions: `DATE()`, `YEAR()`, `MONTH()`, etc.
- Apply {dialect} string functions: `CONCAT()`, `SUBSTRING()`, etc.
- Use {dialect} NULL handling: `IS NULL`, `COALESCE()`, etc.
- Follow {dialect} naming conventions and reserved words

**ERROR PREVENTION:**
- If schema is missing required tables/columns, generate the best possible query and note limitations
- Ensure all parentheses are properly balanced
- Verify all aliases are unique and consistently used
- Confirm query ends with semicolon

**OUTPUT REQUIREMENTS:**
- Generate ONLY the raw SQL query
- NO comments, explanations, or markdown formatting
- NO additional text outside the query
- Ensure query is immediately executable in {dialect}

**Query Complexity Examples:**

**Simple Aggregation:**
```sql
SELECT COUNT(u.user_id) AS user_count
FROM users u
WHERE u.created_date >= '2023-01-01';
```

**Multi-Table JOIN with Aggregation:**
```sql
SELECT
    u.user_name,
    COUNT(o.order_id) AS order_count,
    SUM(o.total_amount) AS total_spent
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE u.status = 'active'
GROUP BY u.user_name
ORDER BY total_spent DESC;
```

**Complex Filtering with Multiple Conditions:**
```sql
SELECT DISTINCT c.customer_id, c.customer_name, c.email
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.registration_date BETWEEN '2023-01-01' AND '2023-12-31'
  AND p.category = 'electronics'
  AND o.status = 'completed';
```

**SQL Query:**"""


    def _get_example_query(self) -> str:
        """Get comprehensive example SQL queries for the prompt."""
        examples = """
        **Example 1: Complex Multi-Table Aggregation Query**
        ```sql
        SELECT
            c.customer_name,
            c.email,
            COUNT(DISTINCT o.order_id) AS total_orders,
            SUM(o.total_amount) AS total_spent,
            AVG(o.total_amount) AS avg_order_value,
            MAX(o.order_date) AS last_order_date
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.product_id
        WHERE c.registration_date BETWEEN '2023-01-01' AND '2023-12-31'
        AND p.category = 'electronics'
        AND o.status = 'completed'
        GROUP BY c.customer_id, c.customer_name, c.email
        HAVING COUNT(o.order_id) > 0
        ORDER BY total_spent DESC, last_order_date DESC;
        ```

        **Example 2: Time-Series Analysis with Window Functions**
        ```sql
        WITH monthly_sales AS (
            SELECT
                DATE_TRUNC('month', o.order_date) AS sale_month,
                p.category,
                SUM(o.total_amount) AS monthly_revenue,
                COUNT(DISTINCT o.order_id) AS order_count,
                ROW_NUMBER() OVER (PARTITION BY p.category ORDER BY SUM(o.total_amount) DESC) AS category_rank
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.order_date >= '2023-01-01'
            GROUP BY DATE_TRUNC('month', o.order_date), p.category
        )
        SELECT
            sale_month,
            category,
            monthly_revenue,
            order_count,
            category_rank
        FROM monthly_sales
        WHERE category_rank <= 3
        ORDER BY sale_month, category_rank;
        ```

        **Example 3: Performance-Optimized Query with Proper Indexing**
        ```sql
        SELECT
            COUNT(DISTINCT c.customer_id) AS active_customer_count
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        LEFT JOIN customer_segments cs ON c.customer_id = cs.customer_id
        WHERE c.registration_date >= '2023-01-01'
        AND c.registration_date < '2024-01-01'
        AND cs.segment_type IN ('premium', 'vip')
        AND o.total_amount > 100.00;
        ```
        """
        return examples
    
    def _extract_query_from_response(self, response: str) -> str:
        """Extract the first valid query from LLM response."""
        if not response or not response.strip():
            return ""

        try:
            # Split response by semicolons and find valid queries
            potential_queries = response.split(';')

            for query_part in potential_queries:
                query_part = query_part.strip()
                if not query_part:
                    continue

                # Clean and validate the query
                clean_query = self._clean_query_text(query_part)
                if self._is_valid_sql_query(clean_query):
                    return clean_query

            logger.warning("⚠️ No valid query found in response")
            return ""

        except Exception as e:
            logger.error(f"❌ Failed to extract query from response: {e}")
            return ""

    def _clean_query_text(self, query_text: str) -> str:
        """Clean query text by removing markdown and comments."""
        lines = query_text.split('\n')
        clean_lines = []

        for line in lines:
            line = line.strip()
            # Skip markdown code blocks and comments
            if (line.startswith('```') or
                line.startswith('--') or
                not line):
                continue
            clean_lines.append(line)

        query = '\n'.join(clean_lines).strip()
        return self._clean_query(query) if 'SELECT' in query.upper() else query

    def _is_valid_sql_query(self, query: str) -> bool:
        """Check if the extracted text is a valid SQL query."""
        return bool(query and 'SELECT' in query.upper())
    
    def _clean_query(self, query: str) -> str:
        """Clean and format the query."""
        try:
            # Remove extra whitespace and normalize
            lines = [line.strip() for line in query.split('\n') if line.strip()]
            
            # Join lines with proper spacing
            cleaned_query = '\n'.join(lines)
            
            # Ensure query ends with semicolon
            if not cleaned_query.endswith(';'):
                cleaned_query += ';'
            
            return cleaned_query
            
        except Exception as e:
            logger.error(f"❌ Failed to clean query: {e}")
            return query
    
    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Extract table names from query using regex."""
        import re
        table_pattern = r'(?:FROM|JOIN)\s+(\w+)'
        matches = re.findall(table_pattern, query, re.IGNORECASE)
        return list(set(matches))  # Remove duplicates

    def _extract_columns_from_query(self, query: str) -> List[str]:
        """Extract column names from SELECT clause."""
        import re
        column_pattern = r'SELECT\s+(.*?)\s+FROM'
        match = re.search(column_pattern, query, re.IGNORECASE | re.DOTALL)

        if not match:
            return []

        columns_text = match.group(1)
        # Parse column names, handling aliases and functions
        columns = []
        for col in columns_text.split(','):
            col = col.strip()
            if not col or col == '*':
                continue
            # Extract the actual column name (before AS or space)
            col_name = col.split()[0].split('(')[-1]  # Handle functions like COUNT(col)
            if col_name and col_name != '*':
                columns.append(col_name)

        return columns
    
    def _get_schema_section(self, state: AgentState) -> str:
        """Get schema information section for the prompt."""
        if state.schema_context and state.schema_context.get("formatted_schema"):
            return f"""**COMPREHENSIVE SCHEMA CONTEXT:**
        {state.schema_context["formatted_schema"]}"""
        else:
            # Fallback to basic information
            return f"""**BASIC SCHEMA INFORMATION:**
        **Databases Available:** {', '.join(state.relevant_databases) if state.relevant_databases else 'None selected'}
        **Tables Available:** {', '.join(state.relevant_tables) if state.relevant_tables else 'None selected'}
        **Columns Available:** {', '.join(state.relevant_columns) if state.relevant_columns else 'None selected'}"""