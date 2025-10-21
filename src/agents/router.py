"""
LLM Router Agent for the text2query system.

This agent acts as the entry point to analyze user queries and determine:
1. Whether the query is a metadata query (like "list all tables", "show databases")
2. What the actual user requirement is

This helps route metadata queries appropriately.
"""

import logging

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from models.models import AgentState, AgentResult, AgentType, RoutingInfo

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    """Agent responsible for routing queries based on their type and requirements."""
    
    def __init__(self, model_wrapper):
        super().__init__(AgentType.LLM_ROUTER, model_wrapper)
    
    def process(self, state: AgentState) -> AgentResult:
        """Analyze the user query and determine routing strategy."""
        logger.info(f"🧭 {self.name}: Analyzing query and determining routing strategy")

        try:
            # Check prerequisites
            if not state.natural_language_query or not state.natural_language_query.strip():
                return AgentUtils.create_error_result("Query text is required for routing")

            # Generate routing analysis
            system_message = self._create_routing_system_prompt()
            human_message = state.natural_language_query

            routing_info = self.generate_with_llm(
                schema_class=RoutingInfo,
                system_message=system_message,
                human_message=human_message,
                temperature=0
            )

            return self._create_success_result(routing_info)

        except Exception as e:
            logger.error(f"❌ Query routing failed: {e}")
            return AgentUtils.create_error_result(str(e))
            

    def _create_success_result(self, routing_info: RoutingInfo) -> AgentResult:
        """Create success result with routing information."""
        state_updates = {
            "is_metadata_query": routing_info.is_metadata_query,
            "dialect": routing_info.dialect,
            "current_step": "query_routed"
        }

        return AgentResult(
            success=True,
            message="Query routing completed successfully",
            state_updates=state_updates
        )
    
    def _create_routing_system_prompt(self) -> str:
        """Create system prompt for query routing analysis."""
        return """You are an intelligent query router for a text2query system. Analyze the user query and determine its type and database dialect.

**Task:** Classify this query as either METADATA or DATA:

**METADATA queries** ask about database structure/schema:
- Database discovery: "show databases", "list all databases", "what databases exist?"
- Table discovery: "list tables", "show all tables", "what tables are in database X?"
- Column information: "what columns are in table X?", "show schema for table Y", "describe table Z"
- Data types: "what is the type of column A in table B?", "show column types for table C"
- Relationships: "show foreign keys", "what tables are related to X?"
- Constraints: "show indexes", "what are the primary keys?"

**DATA queries** ask for actual records/values:
- Record retrieval: "find customers", "show transactions", "get users where..."
- Aggregations: "count of orders", "sum of sales", "average age"
- Filtering: "transactions from last month", "users with pending verification"
- Analysis: "top 10 products", "monthly revenue trends"
- Updates/Inserts: "update customer", "add new record"

**Key Decision Points:**
- If asking WHAT EXISTS → metadata
- If asking FOR ACTUAL VALUES → data
- If asking ABOUT STRUCTURE → metadata
- If asking TO RETRIEVE/MODIFY RECORDS → data

**Database Dialects:**
Detect if query mentions specific database systems:
- PostgreSQL/Postgres keywords: SERIAL, JSONB, ARRAY, etc.
- MySQL keywords: AUTO_INCREMENT, TINYINT, etc.
- SQL Server keywords: IDENTITY, NVARCHAR, etc.
- Oracle keywords: SEQUENCE, VARCHAR2, etc.
- Default to "sql" if no specific dialect detected

Analyze the query and determine the correct routing and dialect.

**CRITICAL: Response Format Requirements:**
- Return ONLY the JSON data object, NOT the schema definition
- Your response must be valid JSON that matches this exact structure:
  ```json
  {{
    "is_metadata_query": true or false,
    "dialect": "sql" or "postgresql" or "mysql" or "sqlserver" or "oracle"
  }}
  ```
- Do NOT include any schema definitions, descriptions, or metadata
- Do NOT wrap your response in markdown code blocks
- The response must be parseable JSON that directly matches the required fields"""