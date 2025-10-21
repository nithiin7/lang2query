"""
Schema Builder Agent for the refined text2query system.

Retrieves comprehensive schema context from the knowledge base for selected tables,
databases, and user queries. Uses schemas to build
formatted schema context that can be used by other agents.
"""

import logging
from typing import List, Dict, Any, Optional

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from models.models import AgentState, AgentResult, AgentType
from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

logger = logging.getLogger(__name__)


class SchemaBuilderAgent(BaseAgent):
    """Agent responsible for building comprehensive schema context using new chunk format."""

    def __init__(self, model_wrapper, retriever: Optional[SQLKnowledgeBaseRetriever] = None):
        super().__init__(AgentType.SCHEMA_BUILDER, model_wrapper)
        self._retriever = retriever

    
    def process(self, state: AgentState) -> AgentResult:
        """Build comprehensive schema context for the given state."""

        try:
            # Validate prerequisites
            validation_error = AgentUtils.validate_state_prerequisites(state, ["relevant_databases", "relevant_tables"])
            if validation_error:
                return validation_error

            # Build comprehensive schema context
            schema_context = self._build_schema_context(
                databases=state.relevant_databases,
                tables=state.relevant_tables,
                user_query=state.natural_language_query
            )

            return self._create_success_result(schema_context)

        except Exception as e:
            logger.error(f"❌ Schema building failed: {e}")
            return AgentUtils.create_error_result(str(e))

    def _build_schema_context(self, databases: List[str], tables: List[str],
                            user_query: str) -> Dict[str, Any]:
        """
        Build comprehensive schema context from schemas.

        Args:
            databases: List of database names
            tables: List of table names (format: "database.table" or just "table")
            user_query: Original user query for context

        Returns:
            Dictionary containing formatted schema context
        """
        logger.info(f"📊 Building schema context for {len(databases)} databases, {len(tables)} tables")

        schema_context = {
            "databases": {},
            "tables": {},
            "formatted_schema": "",
            "summary": {
                "total_databases": len(databases),
                "total_tables": len(tables),
                "query_context": user_query
            }
        }

        # Step 1: Retrieve database information
        for db_name in databases:
            db_info = self._get_database_info(db_name)
            if db_info:
                schema_context["databases"][db_name] = db_info

        # Step 2: Retrieve table and column information
        table_details = self._get_table_details(tables, databases)
        schema_context["tables"] = table_details

        # Step 3: Format comprehensive schema for prompt inclusion
        schema_context["formatted_schema"] = self._format_schema_for_prompt(
            schema_context["databases"],
            schema_context["tables"]
        )

        # Log the formatted schema for review
        logger.info("=== GENERATED SCHEMA CONTEXT ===")
        logger.info(schema_context["formatted_schema"])
        logger.info("=== END SCHEMA CONTEXT ===")

        # Step 4: Update summary statistics
        schema_context["summary"]["total_columns"] = sum(
            len(table_data.get("columns", []))
            for table_data in schema_context["tables"].values()
        )

        return schema_context

    def _get_database_info(self, database_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve database information from schemas."""
        try:
            results = self._retriever.collection.get(
                where={
                    "$and": [
                        {"chunk_type": "database"},
                        {"database_name": database_name}
                    ]
                }
            )

            if results['documents']:
                content = results['documents'][0]
                metadata = results['metadatas'][0] if results['metadatas'] else {}

                return {
                    "name": database_name,
                    "system": metadata.get("system_name", "unknown"),
                    "module": metadata.get("module_name", "unknown"),
                    "content": content,
                    "metadata": metadata
                }
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve database info for '{database_name}': {e}")

        return None

    def _get_table_details(self, tables: List[str], databases: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve comprehensive table details from schemas.

        Args:
            tables: List of table names
            databases: List of database names for context

        Returns:
            Dictionary mapping table names to their complete details
        """
        table_details = {}

        for table in tables:
            # Handle table name formats: "database.table" or just "table"
            if "." in table:
                db_name, table_name = table.split(".", 1)
            else:
                table_name = table
                # Try to match with available databases
                db_name = self._find_database_for_table(table_name, databases)

            if not db_name:
                logger.warning(f"⚠️ Could not determine database for table '{table_name}'")
                continue

            # Get table summary and columns from schemas
            table_info = self._get_table_info(db_name, table_name)
            column_info = self._get_column_info(db_name, table_name)

            if table_info or column_info:
                full_table_name = f"{db_name}.{table_name}"
                table_details[full_table_name] = {
                    "database": db_name,
                    "table": table_name,
                    "summary": table_info,
                    "columns": column_info
                }

        return table_details

    def _find_database_for_table(self, table_name: str, databases: List[str]) -> Optional[str]:
        """Find which database contains the specified table."""
        for db_name in databases:
            # Check if table exists in this database using schemas
            try:
                results = self._retriever.collection.get(
                    where={
                        "$and": [
                            {"chunk_type": "table"},
                            {"database_name": db_name},
                            {"table_name": table_name}
                        ]
                    }
                )
                if results['documents']:
                    return db_name
            except Exception as e:
                logger.debug(f"Error checking table '{table_name}' in database '{db_name}': {e}")

        return None

    def _get_table_info(self, database_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve table information from schemas."""
        try:
            results = self._retriever.collection.get(
                where={
                    "$and": [
                        {"chunk_type": "table"},
                        {"database_name": database_name},
                        {"table_name": table_name}
                    ]
                }
            )

            if results['documents']:
                content = results['documents'][0]
                metadata = results['metadatas'][0] if results['metadatas'] else {}

                # Extract purpose from content (format: "Table: table_name\nPurpose: purpose")
                purpose = "N/A"
                if content:
                    for line in content.split('\n'):
                        if line.startswith('Purpose:'):
                            purpose = line[8:].strip()
                            break

                return {
                    "content": content,
                    "purpose": purpose,
                    "metadata": metadata
                }
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve table info for '{database_name}.{table_name}': {e}")

        return None

    def _get_column_info(self, database_name: str, table_name: str) -> List[Dict[str, Any]]:
        """Retrieve and parse table columns from schemas."""
        try:
            results = self._retriever.collection.get(
                where={
                    "$and": [
                        {"chunk_type": "column"},
                        {"database_name": database_name},
                        {"table_name": table_name}
                    ]
                }
            )

            if results['documents']:
                content = results['documents'][0]
                metadata = results['metadatas'][0] if results['metadatas'] else {}

                # Parse columns from schemas
                columns = self._parse_columns_from_new_format(content, metadata)
                return columns

        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve column info for '{database_name}.{table_name}': {e}")

        return []

    def _parse_columns_from_new_format(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse column information from schemas."""
        columns = []

        try:
            column_names = metadata.get("column_names", [])
            primary_keys = set(metadata.get("primary_keys", []))
            unique_keys = set(metadata.get("unique_keys", []))
            indexed_columns = set(metadata.get("indexed_columns", []))

            # Parse column details from content
            # Format: "column_name data_type constraints nullable description"
            column_lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('Table:')]

            for line in column_lines:
                if not line or line.startswith('Table:'):
                    continue

                # Parse line format: "column_name data_type constraints nullable description"
                parts = line.split()
                if len(parts) < 4:
                    continue

                col_name = parts[0]
                data_type = parts[1]

                # Find constraints and nullable info
                constraints_part = ""
                nullable_part = ""
                description_parts = []

                # Parse the rest of the line to extract constraints and description
                remaining_parts = parts[2:]
                if remaining_parts:
                    # Check for pri/uni/mul constraints
                    constraint_flags = []
                    i = 0
                    while i < len(remaining_parts) and remaining_parts[i].lower() in ['pri', 'uni', 'mul', 'yes', 'no']:
                        if remaining_parts[i].lower() in ['pri', 'uni', 'mul']:
                            constraint_flags.append(remaining_parts[i].lower())
                        elif remaining_parts[i].lower() in ['yes', 'no']:
                            nullable_part = remaining_parts[i].lower()
                            break
                        i += 1

                    # Remaining parts are description
                    description_parts = remaining_parts[i+1:] if i < len(remaining_parts) else remaining_parts[i:]

                column_info = {
                    "name": col_name,
                    "data_type": data_type,
                    "nullable": nullable_part.lower() == "yes" if nullable_part else True,
                    "is_primary_key": "pri" in constraint_flags or col_name in primary_keys,
                    "is_unique": "uni" in constraint_flags or col_name in unique_keys,
                    "is_indexed": "mul" in constraint_flags or col_name in indexed_columns,
                    "constraints": constraint_flags,
                    "description": " ".join(description_parts),
                    "category": ""  # Not available in schemas
                }
                columns.append(column_info)

        except Exception as e:
            logger.warning(f"⚠️ Error parsing columns from schemas: {e}")

        return columns

    def _format_schema_for_prompt(self, databases: Dict[str, Any], 
                                 tables: Dict[str, Dict[str, Any]]) -> str:
        """Format schema information into a comprehensive prompt-ready string."""
        sections: List[str] = []
        sections.extend(self._format_databases_section(databases))
        sections.extend(self._format_tables_section(tables))
        return '\n'.join(sections)

    def _format_databases_section(self, databases: Dict[str, Any]) -> List[str]:
        if not databases:
            return []

        lines = ["**DATABASES:**"]
        for db_name, db_info in databases.items():
            lines.append(f"\n📁 **{db_name}**")
            lines.append(f"   System: {db_info.get('system', 'Unknown')}")
            lines.append(f"   Module: {db_info.get('module', 'Unknown')}")
            purpose = self._extract_purpose_from_content(db_info.get('content'))
            if purpose:
                lines.append(f"   Purpose: {purpose}")
        return lines

    def _extract_purpose_from_content(self, content: Optional[str]) -> str:
        if not content:
            return ""
        for ln in content.split('\n'):
            if ln.startswith('Purpose:'):
                return ln[8:].strip()
        return ""

    def _format_tables_section(self, tables: Dict[str, Dict[str, Any]]) -> List[str]:
        if not tables:
            return []

        lines: List[str] = ["\n\n**TABLES & COLUMNS:**"]
        for table_key, table_data in tables.items():
            lines.extend(self._format_single_table(table_data))
        return lines

    def _format_single_table(self, table_data: Dict[str, Any]) -> List[str]:
        db_name = table_data['database']
        table_name = table_data['table']
        lines = [f"\n🗂️ **{db_name}.{table_name}**"]

        purpose = table_data.get('summary', {}).get('purpose')
        if purpose:
            lines.append(f"   Purpose: {purpose}")

        columns = table_data.get('columns', [])
        if columns:
            lines.append("   Columns:")
            for col in columns:
                lines.append(self._format_single_column(col))

        primary_keys = [col['name'] for col in columns if col.get('is_primary_key')]
        unique_cols = [col['name'] for col in columns if col.get('is_unique')]
        if primary_keys:
            lines.append(f"   Primary Key(s): {', '.join(primary_keys)}")
        if unique_cols:
            lines.append(f"   Unique Column(s): {', '.join(unique_cols)}")
        return lines

    def _format_single_column(self, col: Dict[str, Any]) -> str:
        parts = [f"      • {col['name']} ({col['data_type']})"]
        if col.get('description'):
            parts.append(f" - {col['description']}")

        constraints: List[str] = []
        if col.get('is_primary_key'):
            constraints.append("PK")
        if col.get('is_unique'):
            constraints.append("UNIQUE")
        if col.get('is_indexed'):
            constraints.append("INDEXED")
        if not col.get('nullable', True):
            constraints.append("NOT NULL")

        if constraints:
            parts.append(f" [{', '.join(constraints)}]")
        return ''.join(parts)

    def _create_success_result(self, schema_context: Dict[str, Any]) -> AgentResult:
        """Create success result with schema context."""
        summary = schema_context.get("summary", {})
        
        state_updates = {
            "schema_context": schema_context,
            "current_step": "schema_built"
        }

        return AgentResult(
            success=True,
            message=f"Schema context built for {summary.get('total_databases', 0)} databases and {summary.get('total_tables', 0)} tables",
            state_updates=state_updates
        )
