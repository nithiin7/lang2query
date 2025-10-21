"""
Database Identifier Agent for the refined text2query system.

Identifies which database(s) are most likely to contain the information needed 
to answer the user's query. This is the first layer of filtering in the two-tiered approach.
"""

import logging
from typing import List

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from utils import ChunkParsers
from models.models import AgentState, AgentResult, AgentType, DatabaseSelection

logger = logging.getLogger(__name__)


class DatabaseIdentifierAgent(BaseAgent):
    """Agent responsible for identifying relevant databases for the query."""
    
    def __init__(self, model_wrapper, retriever=None):
        super().__init__(AgentType.DATABASE_IDENTIFIER, model_wrapper)

        self._retriever = retriever
    
    def process(self, state: AgentState) -> AgentResult:
        """Identify relevant databases for the query."""
        logger.info(f"🔍 {self.name}: Identifying relevant databases for query")

        try:
            # Validate prerequisites
            validation_error = AgentUtils.validate_query_text(state)
            if validation_error:
                return validation_error

            system_message = self._create_database_identification_system_prompt(state)
            human_message = state.natural_language_query

            # Generate structured database selection response
            database_selection = self.generate_with_llm(
                schema_class=DatabaseSelection,
                system_message=system_message,
                human_message=human_message,
                temperature=0.1
            )

            # Extract database names from the structured response
            database_names = database_selection.database_names

            return self._create_success_result(database_names)

        except Exception as e:
            logger.error(f"❌ Database identification failed: {e}")
            return AgentUtils.create_error_result(str(e))

    def _create_success_result(self, database_names: List[str]) -> AgentResult:
        """Create success result with database names."""
        logger.info(f"🗄️ Identified databases: {database_names}")

        state_updates = {
            "relevant_databases": database_names,
            "current_step": "databases_identified"
        }

        return AgentResult(
            success=True,
            message="Databases identified successfully",
            state_updates=state_updates
        )
    
    def _create_database_identification_system_prompt(self, state: AgentState) -> str:
        """Create system prompt for database identification."""
        feedback_section = AgentUtils.get_validation_feedback_section(state)
        human_feedback_section = AgentUtils.build_human_feedback_section(state, "database")

        db_section = self._retrieve_relevant_chunks(state.natural_language_query, n_results=10)

        prompt_parts = [
            "You are an expert database architect specializing in multi-database query routing. Your task is to identify ALL databases needed to construct a complete answer to the user's question."
        ]

        if feedback_section:
            prompt_parts.append(feedback_section)
        if human_feedback_section:
            prompt_parts.append(human_feedback_section)
        if db_section:
            prompt_parts.append(db_section)

        prompt_parts.append("""**Critical Database Selection Guidelines:**
1. **ALWAYS include foundational databases**: For queries involving users, customers, or accounts:
   - Include databases containing user/customer/account data as the primary foundation
   - These are typically needed even if not explicitly mentioned in the query
   - Example: A query about "customers who..." almost always needs databases with user/account information

2. **Leverage the detailed database information provided:**
   - **System & Module Analysis**: Review the system names and modules to understand business domains
   - **Database Purpose**: Understanding what each database stores helps determine relevance
   - **Key Tables Overview**: Examine the listed tables to identify data domains (user tables, transaction tables, configuration tables, etc.)
   - **Cross-Database Relationships**: Consider how data in different databases might need to be joined

3. **Identify ALL required data domains**: Break down the query into components:
   - What entities are mentioned? (users, customers, accounts, transactions, etc.)
   - What business domains are involved? (user management, payments, etc.)
   - What specific data types are needed? (profile data, transaction history, verification status, etc.)
   - What cross-domain relationships exist? (user + payment data, customer + verification data, etc.)

4. **Think about data dependencies**: Most complex queries require multiple databases:
   - User/Account databases + Transaction/Payment databases
   - Customer databases + Identity/Verification databases
   - Profile databases + Activity/Audit databases
   - Core business data + Reference/Lookup databases

**Instructions:**
1. **Analyze the query requirements**
   - Break down the user's query to identify required entities, business domains, and data types
   - Map query requirements to databases by examining their purposes and key tables
   - Select ALL databases that contain relevant information for complete query execution
   - Consider that complex queries typically need 2-3 related databases to provide complete answers

2. **Database selection rules**
   - **MANDATORY:** If user-suggested databases are provided, they MUST be included in your selection regardless of whether they appear in the available databases list above
   - Choose database names from the information provided above
   - Provide clear reasoning that references the specific database purposes and key tables you considered
   - If no database contains the required information, return an empty list and explain why in your reasoning

**CRITICAL: Response Format Requirements:**
- Return ONLY the JSON data object, NOT the schema definition
- Your response must be valid JSON that matches this exact structure:
  ```json
  {{
    "reasoning": "Your detailed explanation here",
    "database_names": ["database1", "database2", "database3"]
  }}
  ```
- Do NOT include any schema definitions, descriptions, or metadata
- Do NOT wrap your response in markdown code blocks
- The response must be parseable JSON that directly matches the required fields

**Query Complexity Considerations:**
- **Simple lookups**: May need 1 database (e.g., user profile queries)
- **Transactional queries**: Often need 2+ databases (user data + transaction data)
- **Analytical queries**: Typically need 2-3 databases (entity data + event data + reference data)
- **Cross-domain queries**: Usually require multiple databases from different business domains""")

        return "\n\n".join(prompt_parts)
    

    def _retrieve_relevant_chunks(self, query: str, n_results: int = 5) -> str:
        """Retrieve and format relevant database chunks directly."""
        if not self._retriever:
            return "**Available Databases:**\n(None found)"

        try:
            # Search for database-related chunks
            results = self._retriever.search_by_chunk_type(query, "database", n_results)

            if results and results.get('documents') and results['documents'][0]:
                return ChunkParsers.format_database_chunks(
                    results['documents'][0],
                    results['metadatas'][0]
                )
            else:
                return "**Available Databases:**\n(None found)"

        except Exception as e:
            logger.error(f"Error retrieving database chunks: {e}")
            return "**Available Databases:**\n(None found)"
