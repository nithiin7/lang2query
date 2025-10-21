"""
Common chunk parsing utilities for the Text2Query system.

This module provides unified parsing and formatting functions for different
types of knowledge base chunks (database, table, column).
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ChunkParsers:
    """Common utilities for parsing and formatting knowledge base chunks."""

    @staticmethod
    def format_database_chunks(documents: List[str], metadatas: List[Dict[str, Any]]) -> str:
        """Parse and format database chunks directly from raw documents and metadata."""
        if not documents or not metadatas:
            return "**Available Databases:**\n(None found)"

        # Parse each chunk and collect structured data
        db_infos = []
        for doc, metadata in zip(documents, metadatas):
            db_info = ChunkParsers.parse_database_chunk_with_tables(doc, metadata)
            db_infos.append(db_info)

        # Format the structured data
        formatted_sections = []

        for i, db_info in enumerate(db_infos, 1):
            # Format the database section
            formatted_sections.append(f"--- **Database {i}: {db_info.get('database', 'Unknown')}** ---")
            formatted_sections.append(f"**System:** {db_info.get('system', 'Unknown')}")
            formatted_sections.append(f"**Module:** {db_info.get('module', 'Unknown')}")
            formatted_sections.append(f"**Purpose:** {db_info.get('purpose', 'Not specified')}")

            tables = db_info.get('tables', [])
            if tables:
                formatted_sections.append("**Key Tables:**")
                # Limit to first 5 tables for readability
                for table in tables[:5]:
                    # Format table entries as "name: description" if they contain colon, otherwise just name
                    if ':' in table:
                        table_name, description = table.split(':', 1)
                        formatted_sections.append(f"  • {table_name.strip()}: {description.strip()}")
                    else:
                        formatted_sections.append(f"  • {table.strip()}")
                if len(tables) > 5:
                    formatted_sections.append(f"  ... and {len(tables) - 5} more tables")
            else:
                formatted_sections.append("**Key Tables:** (None listed)")

        return "**Relevant Database Information (from Knowledge Base):**\n" + '\n'.join(formatted_sections)

    @staticmethod
    def format_table_chunks(documents: List[str], metadatas: List[Dict[str, Any]]) -> str:
        """Format table chunks for LLM to identify the best tables to answer user query.
        
        Args:
            documents: List of table chunk contents
            metadatas: List of table chunk metadata
            
        Returns:
            Formatted string with table information including name, database, purpose, and keys
        """
        if not documents or not metadatas:
            return "**Available Tables:**\n(None found)"

        # Parse each chunk and collect structured data
        table_infos = []
        for doc, metadata in zip(documents, metadatas):
            table_info = ChunkParsers.parse_table_chunk_with_keys(doc, metadata)
            table_infos.append(table_info)

        # Format the structured data
        formatted_sections = []

        for i, table_info in enumerate(table_infos, 1):
            formatted_sections.append(f"--- **Table {i}: {table_info.get('table', 'Unknown')}** ---")
            formatted_sections.append(f"**Database:** {table_info.get('database', 'Unknown')}")
            formatted_sections.append(f"**Purpose:** {table_info.get('purpose', 'Not specified')}")
            
            # Format primary keys
            primary_keys = table_info.get('primary_keys', [])
            if primary_keys:
                formatted_sections.append(f"**Primary Keys:** {', '.join(primary_keys)}")
            else:
                formatted_sections.append("**Primary Keys:** (None)")
            
            # Format unique keys
            unique_keys = table_info.get('unique_keys', [])
            if unique_keys:
                formatted_sections.append(f"**Unique Keys:** {', '.join(unique_keys)}")
            else:
                formatted_sections.append("**Unique Keys:** (None)")
            
            formatted_sections.append("")  # Add blank line between tables

        return "**Available Tables (from Knowledge Base):**\n" + '\n'.join(formatted_sections)

    @staticmethod
    def format_table_chunks_filtered_by_databases(results: Dict[str, Any], selected_databases: List[str]) -> str:
        """Format table chunks filtered by selected databases for LLM consumption.
        
        Args:
            results: Retrieval results with 'documents' and 'metadatas' keys
            selected_databases: List of database names to filter by
            
        Returns:
            Formatted string with table information for tables in selected databases
        """
        if not results or not results.get('documents') or not results.get('metadatas'):
            return "**Available Tables:**\n(None found)"

        # Extract documents and metadatas from results
        # Handle both nested list format [[...]] and flat list format [...]
        documents = results['documents']
        metadatas = results['metadatas']
        
        if isinstance(documents[0], list):
            documents = documents[0]
        if isinstance(metadatas[0], list):
            metadatas = metadatas[0]

        # Filter by selected databases
        filtered_docs = []
        filtered_metas = []
        
        for doc, meta in zip(documents, metadatas):
            db_name = meta.get('database_name', '')
            if db_name in selected_databases:
                filtered_docs.append(doc)
                filtered_metas.append(meta)

        # If no tables found in selected databases, return empty message
        if not filtered_docs:
            return "**Available Tables:**\n(None found)"

        # Use the main formatter
        return ChunkParsers.format_table_chunks(filtered_docs, filtered_metas)

    @staticmethod
    def format_column_details(table_columns: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format column details for display in prompts with rich information."""
        if not table_columns:
            return "**Available Columns:**\nNo column details available"

        formatted_sections = []
        formatted_sections.append("**Available Columns (from Knowledge Base):**")

        for table_name, columns in table_columns.items():
            formatted_sections.append(f"\n--- **Table: {table_name}** ---")

            if columns:
                # Sort columns to show primary keys first, then indexed columns, then others
                sorted_columns = sorted(columns, key=lambda x: (
                    not x.get('is_primary_key', False),  # Primary keys first
                    not x.get('is_indexed', False),      # Then indexed columns
                    x.get('name', '')                    # Alphabetical fallback
                ))

                formatted_sections.append("**Columns:**")
                for col in sorted_columns:
                    formatted_sections.append(f"  {ChunkParsers._format_single_column(col)}")
            else:
                formatted_sections.append("**Columns:** No column information available")

        return "\n".join(formatted_sections)

    @staticmethod
    def _format_single_column(column: Dict[str, Any]) -> str:
        """Format a single column with rich metadata information."""
        col_name = column.get('name', 'unknown')
        data_type = column.get('data_type', 'unknown')

        # Build the basic column info
        col_info = f"• {col_name} ({data_type})"

        # Add constraint badges
        badges = []
        if column.get('is_primary_key', False):
            badges.append("PRIMARY KEY")
        if column.get('is_unique', False):
            badges.append("UNIQUE")
        if column.get('is_indexed', False):
            badges.append("INDEXED")

        if badges:
            col_info += f" [{' | '.join(badges)}]"

        # Add additional metadata if available
        additional_info = []
        if column.get('nullable') is not None:
            nullable_status = "NULLABLE" if column['nullable'] else "NOT NULL"
            additional_info.append(nullable_status)

        if column.get('default_value'):
            additional_info.append(f"DEFAULT: {column['default_value']}")

        if column.get('auto_increment', False):
            additional_info.append("AUTO_INCREMENT")

        if column.get('description'):
            additional_info.append(f"Description: {column['description']}")

        if additional_info:
            col_info += f" - {' | '.join(additional_info)}"

        return col_info

    @staticmethod
    def parse_columns_from_chunk(chunk_content: str) -> List[Dict[str, Any]]:
        """Parse detailed column information from a table_columns chunk."""
        columns = []

        try:
            lines = chunk_content.split('\n')

            for line in lines:
                line = line.strip()
                
                # Skip empty lines, header lines, and non-column lines
                if not line or not line[0].isalpha():
                    continue
                
                # Skip header lines like "Table:", "Purpose:", etc.
                if line.startswith(('Table:', 'Purpose:', 'Database:', 'Type:')):
                    continue

                # Parse the detailed column format: name type constraint nullable [default] [auto_increment] [description]
                # Example: id bigint(20) pri no auto_increment id
                # Example: cust_id bigint(20) uni no customer id
                # Example: status tinyint(1) yes
                parts = line.split()
                if len(parts) < 3:
                    continue

                col_name = parts[0]
                data_type = parts[1]

                # Determine if parts[2] is a constraint or nullable indicator
                # Constraints: pri, uni, mul
                # Nullable: yes, no
                remaining_parts = parts[2:]
                constraint = ""
                nullable = "yes"
                extra_start_idx = 0
                
                if len(remaining_parts) > 0:
                    first_part = remaining_parts[0].lower()
                    # Check if it's a constraint keyword
                    if first_part in ['pri', 'uni', 'mul']:
                        constraint = remaining_parts[0]
                        nullable = remaining_parts[1] if len(remaining_parts) > 1 else "yes"
                        extra_start_idx = 2
                    # Check if it's a nullable keyword
                    elif first_part in ['yes', 'no']:
                        nullable = remaining_parts[0]
                        extra_start_idx = 1
                    else:
                        # Unexpected format, treat as nullable
                        nullable = remaining_parts[0]
                        extra_start_idx = 1
                
                # Get remaining parts after constraint and nullable
                extra_parts = remaining_parts[extra_start_idx:] if len(remaining_parts) > extra_start_idx else []
                
                # Check if auto_increment is present
                is_auto_increment = 'auto_increment' in extra_parts
                
                # Extract default value and description
                default_val = ""
                description = ""
                
                if extra_parts:
                    if is_auto_increment:
                        # Find auto_increment position
                        auto_inc_idx = extra_parts.index('auto_increment')
                        # Everything before is default value (if any)
                        if auto_inc_idx > 0:
                            default_val = ' '.join(extra_parts[:auto_inc_idx])
                        # Everything after is description
                        if auto_inc_idx + 1 < len(extra_parts):
                            description = ' '.join(extra_parts[auto_inc_idx + 1:])
                    else:
                        # No auto_increment
                        # Check if first part looks like a default value
                        first_part = extra_parts[0].lower()
                        if first_part in ['null', '0', '1', 'current_timestamp', "''", '""'] or first_part.isdigit():
                            default_val = extra_parts[0]
                            description = ' '.join(extra_parts[1:]) if len(extra_parts) > 1 else ""
                        else:
                            # Assume it's all description
                            description = ' '.join(extra_parts)

                # Determine boolean flags
                is_primary_key = 'pri' in constraint.lower()
                is_unique = 'uni' in constraint.lower()
                is_indexed = 'mul' in constraint.lower()
                is_nullable = nullable.lower() == 'yes'

                # Clean up data type (remove parentheses content for display)
                if '(' in data_type:
                    data_type = data_type.split('(')[0]

                column_info = {
                    "name": col_name,
                    "data_type": data_type,
                    "is_primary_key": is_primary_key,
                    "is_unique": is_unique,
                    "is_indexed": is_indexed,
                    "nullable": is_nullable,
                    "default_value": default_val.strip() if default_val else None,
                    "auto_increment": is_auto_increment,
                    "description": description.strip() if description else None
                }

                columns.append(column_info)

        except Exception as e:
            logger.error(f"Error parsing columns from chunk: {e}")

        return columns

    @staticmethod
    def extract_database_purpose(chunk_content: str) -> str:
        """Extract database purpose from a database chunk content."""
        if not chunk_content:
            return "N/A"

        lines = chunk_content.split('\n')
        for line in lines:
            if line.startswith('Purpose:'):
                return line[8:].strip()
        return "N/A"

    @staticmethod
    def extract_table_purpose(chunk_content: str) -> str:
        """Extract table purpose from a table chunk content."""
        if not chunk_content:
            return "N/A"

        lines = chunk_content.split('\n')
        for line in lines:
            if line.startswith('Purpose:'):
                return line[8:].strip()
        return "N/A"

    @staticmethod
    def parse_database_chunk(chunk_content: str, metadata: dict) -> Dict[str, Any]:
        """Parse a complete database chunk into structured data."""
        purpose = ChunkParsers.extract_database_purpose(chunk_content)

        return {
            'database': metadata.get('database_name', 'unknown'),
            'system': metadata.get('system_name', 'unknown'),
            'module': metadata.get('module_name', 'unknown'),
            'purpose': purpose
        }

    @staticmethod
    def parse_table_chunk(chunk_content: str, metadata: dict) -> Dict[str, Any]:
        """Parse a complete table chunk into structured data."""
        purpose = ChunkParsers.extract_table_purpose(chunk_content)

        return {
            'table': metadata.get('table_name', 'unknown'),
            'database': metadata.get('database_name', 'unknown'),
            'purpose': purpose[:60] + '...' if len(purpose) > 60 else purpose
        }

    @staticmethod
    def parse_table_chunk_with_keys(chunk_content: str, metadata: dict) -> Dict[str, Any]:
        """Parse a complete table chunk into structured data with keys information."""
        purpose = ChunkParsers.extract_table_purpose(chunk_content)

        # Get primary and unique keys from metadata
        # Note: ChromaDB stores lists as comma-separated strings
        primary_keys = metadata.get('primary_keys', [])
        unique_keys = metadata.get('unique_keys', [])
        
        # Convert comma-separated strings back to lists if needed
        if isinstance(primary_keys, str):
            primary_keys = [k.strip() for k in primary_keys.split(',') if k.strip()]
        if isinstance(unique_keys, str):
            unique_keys = [k.strip() for k in unique_keys.split(',') if k.strip()]

        return {
            'table': metadata.get('table_name', 'Unknown'),
            'database': metadata.get('database_name', 'Unknown'),
            'purpose': purpose if purpose else 'Not specified',
            'primary_keys': primary_keys if primary_keys else [],
            'unique_keys': unique_keys if unique_keys else []
        }

    @staticmethod
    def parse_database_chunk_with_tables(chunk_content: str, metadata: dict) -> Dict[str, Any]:
        """Parse a complete database chunk into structured data with tables information."""
        lines = chunk_content.split('\n')
        db_info = {
            'database': metadata.get('database_name', 'Unknown'),
            'system': 'Unknown',
            'module': metadata.get('module_name', 'Unknown'),
            'purpose': 'Not specified',
            'tables': []
        }

        # Parse the content
        in_tables_section = False
        for line in lines:
            line = line.strip()
            if line.startswith('System:'):
                db_info['system'] = line.replace('System:', '').strip()
            elif line.startswith('Purpose:'):
                db_info['purpose'] = line.replace('Purpose:', '').strip()
            elif line.startswith('Key Tables:'):
                in_tables_section = True
            elif in_tables_section and line.startswith('- '):
                table_info = line[2:].strip()  # Remove "- "
                # Skip summary lines that start with "... and"
                if table_info and not table_info.startswith('... and'):
                    db_info['tables'].append(table_info)

        return db_info