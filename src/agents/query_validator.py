"""
Query Validator Agent

A minimal LLM-backed validator that checks whether the generated query
matches the user's intent by asking the model for a simple YES/NO
assessment with a short reason. The agent then updates the workflow
state accordingly.
"""

import logging
from datetime import datetime

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from models.models import AgentState, AgentResult, AgentType, QueryValidation
from tools.date_tools import get_current_date


logger = logging.getLogger(__name__)


class QueryValidatorAgent(BaseAgent):
    """Lightweight validator that compares user query vs generated query."""

    def __init__(self, model_wrapper, retriever=None):
        super().__init__(AgentType.QUERY_VALIDATOR, model_wrapper)
        self._retriever = retriever

    def process(self, state: AgentState) -> AgentResult:
        """Validate whether the generated query matches the user's request."""
        logger.info("🔍 Performing LLM-based query validation")

        try:
            # Check prerequisites
            if not state.generated_query or not state.generated_query.query:
                return AgentUtils.create_error_result("No query generated; cannot validate")

            # Build schema and validation prompt using new message format
            system_message = self._build_validation_system_prompt(state)
            human_message = f"""USER REQUEST:
{state.natural_language_query}

GENERATED QUERY:
{state.generated_query.query}"""

            tools = [get_current_date]

            # Generate structured validation response
            validation_result = self.generate_with_llm(
                schema_class=QueryValidation,
                system_message=system_message,
                human_message=human_message,
                tools=tools,
                temperature=0.4
            )

            # Extract validation results
            is_valid = validation_result.verdict == "YES"
            reason = validation_result.reason
            reason_code = validation_result.reason_code.value

            # Classify issue type
            issue_type = reason_code or 'unknown'

            # Create feedback
            feedback = self._create_feedback(is_valid, issue_type, reason, str(validation_result.model_dump()), state)

            return AgentResult(
                success=True,
                message=f"Validation result: {'valid' if is_valid else 'invalid'}",
                state_updates={
                    "is_query_valid": is_valid,
                    "query_validation_feedback": feedback,
                    "last_error_type": None if is_valid else issue_type,
                    "current_step": "query_validated",
                }
            )

        except Exception as e:
            logger.error(f"❌ Query validation failed: {e}")
            return AgentUtils.create_error_result(str(e))


    def _build_validation_system_prompt(self, state: AgentState) -> str:
        """Create a structured validation system prompt with schema context."""

        schema_section = self._get_schema_section(state)

        return f"""You are an expert SQL query validator. Evaluate if the GENERATED QUERY adequately answers the USER REQUEST. Be LENIENT - accept queries that are "close enough" and can be improved through the feedback loop. Only reject queries with major flaws.

VALIDATION GUIDELINES:

**ACCEPT (YES) if the query is "good enough":**
- Basic structure is sound even if minor details could be improved
- Core logic matches user intent, even with small imperfections
- Query would produce usable results that address the main request

**REJECT (NO) for these specific issues:**
- Query uses tables/columns that don't exist in schema
- SQL syntax is completely broken and unexecutable
- Query logic is fundamentally wrong (e.g., counting instead of listing)
- Critical missing components that make results useless
- Missing required WHERE clauses for time-sensitive queries
- Incorrect aggregation functions (COUNT vs SUM vs AVG)
- JOIN conditions that don't match the logical relationships in the request

VALIDATION CHECKLIST:
1. **Can this query run?** (basic syntax and schema validity)
2. **Does it address the core request?** (right general approach)
3. **Are results usable?** (would provide value even if not perfect)
4. **Time/date filters present?** (for queries mentioning dates/periods)
5. **Correct aggregation?** (COUNT for counting, SUM for totals, etc.)
6. **Proper JOIN logic?** (relationships match the request intent)

**Requirements:**
    - If verdict is "YES":
        - Set reason to a brief success summary (e.g., "Covers core intent; minor date refinement possible").
        - Set reason_code to "accepted" (or "accepted_with_minor_issues" if applicable).
    - If verdict is "NO":
        - Provide a concrete, actionable "reason".
        - Choose the most relevant error "reason_code" from the list.

{schema_section}

REASON CODE SEMANTICS:
- schema_missing: Missing tables, columns, or relationships prevent any meaningful query
- sql_generation_issue: Major SQL syntax errors or fundamentally wrong logic
- insufficient_data: User's request lacks critical details making any query impossible
- query_scope_issue: Query scope is completely wrong (e.g., wrong table, completely wrong time period)
- data_type_mismatch: Critical data type issues that break the query logic
- join_relationship_error: Missing or wrong joins that make results meaningless
- unknown: Cannot classify; use as last resort

*** Use the tools provided to you to get the current date and time. ***

EXAMPLES OF VALIDATION:

ACCEPT THESE ("YES" - good enough for now):
- Request: "Show customer names who bought in January 2024"
  Query: "SELECT customer_name FROM orders WHERE order_date >= '2024-01-01' AND order_date < '2024-02-01'"
  → verdict: "YES" (date logic works, can be refined later)

- Request: "Count active users this month"
  Query: "SELECT COUNT(*) FROM users WHERE last_login > '2024-09-01'"
  → verdict: "YES" (reasonable approximation, date can be adjusted)

REJECT THESE ("NO" - now stricter on these issues):
- Request: "Show customer names who bought in January 2024"
  Query: "SELECT customer_name FROM orders" (missing WHERE clause for date filter)
  → verdict: "NO", reason: "Missing required date filter for time-sensitive query", reason_code: "query_scope_issue"

- Request: "Count active users this month"
  Query: "SELECT name FROM users" (no aggregation for counting request)
  → verdict: "NO", reason: "Missing COUNT() aggregation for counting request", reason_code: "sql_generation_issue"

- Request: "Show top 10 products by sales"
  Query: "SELECT product_name, COUNT(amount) FROM sales GROUP BY product_name ORDER BY COUNT(amount) DESC LIMIT 10"
  → verdict: "NO", reason: "Using COUNT instead of SUM for sales totals", reason_code: "sql_generation_issue"

- Request: "Show customer names who bought in January 2024"
  Query: "SELECT customer_id FROM products WHERE product_name = 'Widget'"
  → verdict: "NO", reason: "Query uses completely wrong tables and logic", reason_code: "sql_generation_issue"

**CRITICAL: Response Format Requirements:**
- Return ONLY the JSON data object, NOT the schema definition
- Your response must be valid JSON that matches this exact structure:
  ```json
  {{
    "verdict": "YES" or "NO",
    "reason": "Your detailed explanation here",
    "reason_code": "accepted" or "accepted_with_minor_issues" or "schema_missing" or "sql_generation_issue" or "insufficient_data" or "query_scope_issue" or "data_type_mismatch" or "join_relationship_error" or "unknown"
  }}
  ```
- Do NOT include any schema definitions, descriptions, or metadata
- Do NOT wrap your response in markdown code blocks
- The response must be parseable JSON that directly matches the required fields

"""


    def _create_feedback(self, is_valid: bool, issue_type: str, reason: str, llm_response: str, state: AgentState) -> dict:
        """Create validation feedback dictionary."""
        existing = state.query_validation_feedback or {}

        feedback = {
            "overall_valid": is_valid,
            "total_issues": existing.get("total_issues", 0) + (0 if is_valid else 1),
            "suggestions": existing.get("suggestions", []) + ([] if is_valid else ["Regenerate query based on user intent"]),
            "llm_judgment": llm_response,
            "reason": reason,
            "issue_type": issue_type,
            "reason_code": issue_type,
        }

        # Add to history if existing feedback exists
        if existing:
            feedback["validation_history"] = existing.get("validation_history", []) + [{
                "timestamp": datetime.now().isoformat(),
                "overall_valid": is_valid,
                "llm_judgment": llm_response,
                "reason": reason,
                "issue_type": issue_type,
            }]

        return feedback
    
    def _get_schema_section(self, state: AgentState) -> str:
        """Get schema information section for the prompt."""
        if state.schema_context and state.schema_context.get("formatted_schema"):
            return f"""**AVAILABLE SCHEMA CONTEXT:**
        {state.schema_context["formatted_schema"]}"""
        else:
            # Fallback to basic information
            return f"""**BASIC SCHEMA INFORMATION:**
        **Databases:** {', '.join(state.relevant_databases) if state.relevant_databases else 'None'}
        **Tables:** {', '.join(state.relevant_tables) if state.relevant_tables else 'None'}
        **Columns:** {', '.join(state.relevant_columns) if state.relevant_columns else 'None'}"""
