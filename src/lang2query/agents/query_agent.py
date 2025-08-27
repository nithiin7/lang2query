"""Query generation agent for converting natural language to SQL queries."""

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from ..utils.db_parser import DatabaseSchema, MarkdownDBParser
from ..utils.logger import logger


class SQLQuery(BaseModel):
    """Represents a generated SQL query."""

    query: str = Field(description="The generated SQL query")
    explanation: str = Field(description="Explanation of what the query does")
    tables_used: List[str] = Field(description="List of tables used in the query")
    confidence: float = Field(
        description="Confidence score (0-1) for the generated query"
    )


class QueryGenerationAgent:
    """Agent for generating SQL queries from natural language using database schema."""

    def __init__(
        self, api_key: Optional[str], db_metadata_path: str = "db_metadata.md"
    ):
        secret_key: Optional[SecretStr] = SecretStr(api_key) if api_key else None
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=secret_key, temperature=0.1)
        self.db_parser = MarkdownDBParser(db_metadata_path)
        self.output_parser = JsonOutputParser(pydantic_object=SQLQuery)

    def generate_query(self, user_request: str) -> SQLQuery:
        """Generate a SQL query from a natural language request."""
        try:
            # Parse the database schema
            schema = self.db_parser.parse()

            # Create the system prompt with schema information
            system_prompt = self._create_system_prompt(schema)

            # Create the user message
            user_message = HumanMessage(content=user_request)

            # Generate the response
            response = self.llm.invoke([system_prompt, user_message])

            # Parse the response
            content_str = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )
            query_data = self.output_parser.parse(content_str)

            # Create SQLQuery object
            sql_query = SQLQuery(**query_data)

            logger.info(f"Generated SQL query: {sql_query.query}")
            logger.info(f"Tables used: {sql_query.tables_used}")

            return sql_query

        except Exception as e:
            logger.error(f"Error generating query: {e}")
            # Return a fallback query
            return SQLQuery(
                query="-- Error generating query",
                explanation=f"Failed to generate query: {str(e)}",
                tables_used=[],
                confidence=0.0,
            )

    def _create_system_prompt(self, schema: DatabaseSchema) -> SystemMessage:
        """Create a system prompt with database schema information."""

        # Build schema description
        schema_desc = "Database Schema:\n\n"

        for table_name, table in schema.tables.items():
            schema_desc += f"Table: {table_name}\n"
            schema_desc += "Columns:\n"

            for col in table.columns:
                nullable = "NOT NULL" if col.nullable else "NULL"
                key_info = f" ({col.key_type})" if col.key_type != "-" else ""
                col_line = f"  - {col.name}: {col.data_type} {nullable}{key_info}"
                col_line += f" - {col.description} [{col.category}]\n"
                schema_desc += col_line

            if table.relationships:
                schema_desc += "Relationships:\n"
                for rel in table.relationships:
                    schema_desc += f"  - {rel}\n"

            schema_desc += "\n"

        if schema.notes:
            schema_desc += "Notes:\n"
            for note in schema.notes:
                schema_desc += f"- {note}\n"
            schema_desc += "\n"

        # Add instructions
        instructions = """
            You are a SQL query generation expert. Your task is to convert natural 
            language requests into accurate SQL queries.

            IMPORTANT RULES:
            1. Use the exact table and column names from the schema above
            2. Generate standard SQL (compatible with most databases)
            3. Use appropriate JOINs when multiple tables are needed
            4. Consider the relationships between tables
            5. Use proper SQL syntax and formatting
            6. If the request is ambiguous, make reasonable assumptions and note them 
               in the explanation
            7. Always include an ORDER BY clause when retrieving multiple records 
               (use appropriate columns)
            8. Use LIMIT when appropriate to prevent large result sets

            Return your response as a JSON object with:
            - query: The SQL query string
            - explanation: Clear explanation of what the query does
            - tables_used: List of table names used in the query
            - confidence: Confidence score from 0.0 to 1.0

            Example response format:
            {
            "query": "SELECT u.username, o.order_date, o.total_amount FROM users u 
                     JOIN orders o ON u.id = o.user_id WHERE o.status = 'pending' 
                     ORDER BY o.order_date DESC LIMIT 10",
            "explanation": "This query retrieves pending orders with user information, 
                           showing username, order date, and total amount, ordered by 
                           most recent first and limited to 10 results.",
            "tables_used": ["users", "orders"],
            "confidence": 0.95
            }
        """

        full_prompt = schema_desc + instructions

        return SystemMessage(content=full_prompt)

    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate a generated SQL query for basic syntax and safety."""
        validation_result: Dict[str, Any] = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
        }

        # Basic SQL injection prevention
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "INSERT",
            "UPDATE",
        ]
        query_upper = query.upper()

        for keyword in dangerous_keywords:
            if keyword in query_upper:
                validation_result["warnings"].append(
                    f"Query contains {keyword} operation - ensure this is intentional"
                )

        # Check for basic SQL structure
        if not query.strip().upper().startswith("SELECT"):
            validation_result["warnings"].append(
                "Query should start with SELECT for read operations"
            )

        # Check for proper table references
        schema = self.db_parser.parse()
        valid_tables = set(schema.tables.keys())

        # Simple table name extraction (this could be improved with proper SQL parsing)
        for table in valid_tables:
            if table.lower() in query.lower():
                break
        else:
            validation_result["warnings"].append(
                "Query may not reference any tables from the schema"
            )

        return validation_result
