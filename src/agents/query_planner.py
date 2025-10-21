"""
Query Planner Agent for the refined text2query system.

Creates a logical, step-by-step plan in natural language for how to answer the user's question.
This is a crucial reasoning step that happens before any SQL is written.
"""

import logging
import json

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from models.models import AgentState, AgentResult, AgentType, QueryPlan
from tools.date_tools import get_current_date

logger = logging.getLogger(__name__)


class QueryPlannerAgent(BaseAgent):
    """Agent responsible for creating a logical query plan."""
    
    def __init__(self, model_wrapper, retriever=None):
        super().__init__(AgentType.QUERY_PLANNER, model_wrapper)
        self._retriever = retriever
    
    def process(self, state: AgentState) -> AgentResult:
        """Create a step-by-step query plan based on the question and schema."""
        logger.info(f"🧠 {self.name}: Creating query plan")

        try:
            # Validate prerequisites
            field_checks = [
                ("relevant_databases", "No databases found, cannot create query plan"),
                ("relevant_tables", "No tables found, cannot create query plan"),
                ("relevant_columns", "No columns found, cannot create query plan"),
            ]
            validation_error = AgentUtils.validate_multiple_fields(state, field_checks)
            if validation_error:
                return validation_error

            # Generate structured query plan response
            system_message = self._create_planning_system_prompt(state)
            human_message = state.natural_language_query
            tools = [get_current_date]

            query_plan_result = self.generate_with_llm(
                schema_class=QueryPlan,
                system_message=system_message,
                human_message=human_message,
                tools=tools,
                temperature=0.4
            )

            return self._create_success_result(query_plan_result)

        except Exception as e:
            logger.error(f"❌ Query planning failed: {e}")
            return AgentUtils.create_error_result(str(e))


    def _create_success_result(self, query_plan_result: QueryPlan) -> AgentResult:
        """Create success result with query plan."""
        query_plan_json = json.dumps(query_plan_result.model_dump(), indent=2)

        state_updates = {
            "query_plan": query_plan_json,
            "current_step": "query_planned"
        }

        return AgentResult(
            success=True,
            message="Query plan created successfully",
            state_updates=state_updates
        )

    
    def _create_planning_system_prompt(self, state: AgentState) -> str:
        """Create system prompt for query planning with dynamic sections."""

        feedback_section = AgentUtils.get_validation_feedback_section(state)

        schema_section = self._get_schema_section(state)

        return f"""
        You are a Senior Principal Data Architect specializing in complex query planning and optimization. Your task is to create a comprehensive, executable query plan that systematically breaks down the user's question into precise database operations.

        **Columns Selected by Column Identifier Agent that can be used in the plan:**
        {state.relevant_columns}

        {schema_section}

        {feedback_section}
        ```

        **SYSTEMATIC QUERY PLANNING PROCESS:**

        **Phase 1: Query Analysis & Decomposition**
        1. **Identify Query Intent:** Determine the primary operation (COUNT, SUM, LIST, FIND, etc.)
        2. **Break Down Requirements:** Identify all entities, conditions, filters, and outputs needed
        3. **Determine Query Complexity:** Assess if this is a simple query, aggregation, multi-table join, or complex analytical query

        **Phase 2: Schema Validation & Gap Analysis**
        1. **Table Sufficiency:** Verify all required tables are present and accessible
        2. **Column Availability:** Confirm all needed columns exist with appropriate data types
        3. **Relationship Integrity:** Validate that JOIN keys exist and have compatible data types
        4. **Data Flow Analysis:** Map out how data will flow from source tables to final result
        5. **Identify Gaps:** If schema is insufficient, specify exactly what tables/columns/relationships are missing

        **Phase 3: Query Structure Design**
        1. **Base Table Selection:** Choose the primary table(s) to start the query from
        2. **JOIN Strategy:** Design the optimal JOIN path with explicit key relationships
        3. **Filtering Logic:** Plan WHERE conditions, including date ranges and status filters as mentioned in the user's query
        4. **Aggregation Strategy:** Determine GROUP BY, HAVING, and aggregate function requirements
        5. **Sorting & Limiting:** Plan ORDER BY and LIMIT/OFFSET clauses

        **Phase 4: Performance & Optimization**
        1. **Index Utilization:** Identify which columns should use indexes for filtering
        2. **Query Efficiency:** Choose optimal JOIN order and filtering sequence
        3. **Data Volume Assessment:** Consider result set sizes and potential performance implications

        **CRITICAL PLANNING GUIDELINES:**

        **Data Entity Mapping:**
        - **Users/Customers:** Map to user/customer/account tables
        - **Transactions/Orders:** Map to transaction/order/payment tables
        - **Time-based Data:** Map to tables with date/timestamp columns
        - **Status/Categories:** Map to lookup or status tables

        **JOIN Path Specification:**
        - **ALWAYS specify exact column names** for JOIN conditions (e.g., "users.user_id = orders.user_id")
        - **Document the complete JOIN chain** for complex multi-table queries
        - **Consider JOIN types** (INNER, LEFT, RIGHT) based on data requirements
        - **Optimize JOIN order** starting from smallest result sets

        **Filtering & Conditions:**
        - **Date Range Handling:** Use explicit date formats and ranges
        - **Status Filtering:** Include appropriate status checks and NULL handling
        - **Multi-condition Logic:** Properly handle AND/OR combinations
        - **Performance Filters:** Apply restrictive conditions early in the query

        **Aggregation & Analytics:**
        - **GROUP BY Requirements:** Include all non-aggregated columns in GROUP BY
        - **HAVING Conditions:** Apply filters on aggregated results
        - **Window Functions:** Consider ROW_NUMBER, RANK for complex analytics
        - **Subquery Usage:** Plan for subqueries when needed for complex logic

        **Instructions:**
        1. **Schema Assessment:** Provide a comprehensive evaluation including:
           - Table and column sufficiency analysis
           - Relationship integrity assessment
           - Missing components identification
           - Performance implications

        2. **Detailed Execution Plan:** Provide a step-by-step plan that includes:
           - Specific table and column references
           - Exact JOIN conditions with column names
           - Complete filter conditions
           - Aggregation specifications
           - Performance optimization notes

        3. **Quality Assurance:** Ensure the plan is:
           - **Executable:** Contains all necessary components for SQL generation
           - **Optimized:** Considers performance and efficiency
           - **Complete:** Addresses all aspects of the user's question
           - **Clear:** Uses precise table and column names

        *** Verify the plan with the user's query and make sure it is correct. ***
        *** Ensure your query plan is designed to maximize data retrieval, enabling the user to obtain the most best results possible from the query. ***
        *** Use the tools provided to you to get the current date and time. ***

        **CRITICAL: Response Format Requirements:**
        - Return ONLY the JSON data object, NOT the schema definition
        - Your response must be valid JSON that matches this exact structure:
          ```json
          {{
            "schema_assessment": "Your detailed schema analysis here",
            "plan": ["Step 1: description", "Step 2: description", "Step 3: description"]
          }}
          ```
        - Do NOT include any schema definitions, descriptions, or metadata
        - Do NOT wrap your response in markdown code blocks
        - The response must be parseable JSON that directly matches the required fields

        **Advanced Query Patterns:**

        **Complex Sales Analytics:**
        ```
        1. Start with orders table filtered by date range and status
        2. JOIN to customers table on customer_id for customer information
        3. LEFT JOIN to order_items table on order_id for product details
        4. JOIN to products table on product_id for product attributes
        5. Apply category filters and price range conditions
        6. GROUP BY customer attributes and aggregate sales metrics
        7. Apply HAVING conditions for minimum purchase thresholds
        8. ORDER by revenue metrics for ranking
        ```

        **Time-Series Analysis:**
        ```
        1. Identify base entity (orders, transactions, events, etc.)
        2. Apply date range filters using appropriate timestamp columns
        3. JOIN related tables maintaining temporal relationships
        4. Group by time periods (day, week, month, quarter, year) as needed
        5. Apply time-based aggregations and window functions
        6. Sort chronologically for trend analysis
        ```

        **Inventory Management:**
        ```
        1. Start with products table filtered by category or status
        2. JOIN to inventory_levels table on product_id for stock information
        3. LEFT JOIN to suppliers table on supplier_id for supplier details
        4. Apply stock level filters and reorder point conditions
        5. GROUP BY product categories and aggregate inventory metrics
        6. Apply HAVING conditions for low stock alerts
        7. ORDER by stock levels for priority handling
        ```

        """
    
    def _get_schema_section(self, state: AgentState) -> str:
        """Get schema information section for the prompt."""
        if state.schema_context and state.schema_context.get("formatted_schema"):
            return f"""**SCHEMA CONTEXT:**
        {state.schema_context["formatted_schema"]}"""
        else:
            # Fallback to basic information
            return f"""**BASIC SCHEMA INFORMATION:**
        **Databases Available:** {', '.join(state.relevant_databases) if state.relevant_databases else 'None selected'}
        **Tables Available:** {', '.join(state.relevant_tables) if state.relevant_tables else 'None selected'}
        **Columns Available:** {', '.join(state.relevant_columns) if state.relevant_columns else 'None selected'}"""