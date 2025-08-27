"""Database metadata parser for markdown files."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class Column:
    """Represents a database column."""

    name: str
    data_type: str
    nullable: bool
    key_type: str
    description: str
    category: str


@dataclass
class Table:
    """Represents a database table."""

    name: str
    columns: List[Column]
    relationships: List[str]


@dataclass
class DatabaseSchema:
    """Represents the complete database schema."""

    tables: Dict[str, Table]
    notes: List[str]


class MarkdownDBParser:
    """Parser for database metadata stored in markdown format."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def parse(self) -> DatabaseSchema:
        """Parse the markdown file and return a DatabaseSchema object."""
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Database metadata file not found: {self.file_path}"
            )

        content = self.file_path.read_text()

        # Parse tables
        tables = self._parse_tables(content)

        # Parse relationships
        relationships = self._parse_relationships(content)

        # Parse notes
        notes = self._parse_notes(content)

        # Update tables with relationships
        for table_name, table in tables.items():
            if table_name in relationships:
                table.relationships = relationships[table_name]

        return DatabaseSchema(tables=tables, notes=notes)

    def _parse_tables(self, content: str) -> Dict[str, Table]:
        """Parse table definitions from markdown content."""
        tables = {}

        # Find table sections
        table_pattern = r"### (\w+)\n\|.*?\n\|.*?\n((?:\|.*?\n)*)"
        table_matches = re.finditer(table_pattern, content, re.DOTALL)

        for match in table_matches:
            table_name = match.group(1)
            table_content = match.group(2)

            columns = self._parse_columns(table_content)
            tables[table_name] = Table(
                name=table_name, columns=columns, relationships=[]
            )

        return tables

    def _parse_columns(self, table_content: str) -> List[Column]:
        """Parse column definitions from table content."""
        columns = []

        # Split into lines and skip header separators
        lines = [
            line.strip()
            for line in table_content.split("\n")
            if line.strip() and not line.startswith("|-")
        ]

        for line in lines:
            if line.startswith("|"):
                # Remove leading/trailing pipes and split
                parts = [part.strip() for part in line[1:-1].split("|")]

                if len(parts) >= 6:
                    column = Column(
                        name=parts[0],
                        data_type=parts[1],
                        nullable=parts[2] == "NOT NULL",
                        key_type=parts[3],
                        description=parts[4],
                        category=parts[5],
                    )
                    columns.append(column)

        return columns

    def _parse_relationships(self, content: str) -> Dict[str, List[str]]:
        """Parse table relationships from markdown content."""
        relationships: Dict[str, List[str]] = {}

        # Find relationships section
        rel_pattern = r"## Relationships\n((?:- .*?\n)*)"
        rel_match = re.search(rel_pattern, content, re.DOTALL)

        if rel_match:
            rel_content = rel_match.group(1)
            lines = [line.strip() for line in rel_content.split("\n") if line.strip()]

            for line in lines:
                if line.startswith("- "):
                    # Extract table names from relationship line
                    # Format: "table1 (1) → (N) table2"
                    parts = line[2:].split(" → ")
                    if len(parts) == 2:
                        table1 = parts[0].split(" ")[0]
                        table2 = parts[1].split(" ")[-1]

                        if table1 not in relationships:
                            relationships[table1] = []
                        if table2 not in relationships:
                            relationships[table2] = []

                        relationships[table1].append(line[2:])
                        relationships[table2].append(line[2:])

        return relationships

    def _parse_notes(self, content: str) -> List[str]:
        """Parse notes section from markdown content."""
        notes: List[str] = []

        # Find notes section
        notes_pattern = r"## Notes\n((?:- .*?\n)*)"
        notes_match = re.search(notes_pattern, content, re.DOTALL)

        if notes_match:
            notes_content = notes_match.group(1)
            lines = [line.strip() for line in notes_content.split("\n") if line.strip()]

            for line in lines:
                if line.startswith("- "):
                    notes.append(line[2:])

        return notes

    def get_schema_summary(self) -> str:
        """Get a human-readable summary of the database schema."""
        schema = self.parse()

        summary = "Database Schema Summary:\n\n"

        for table_name, table in schema.tables.items():
            summary += f"Table: {table_name}\n"
            summary += f"  Columns: {len(table.columns)}\n"

            # Group columns by category
            categories: Dict[str, List[str]] = {}
            for col in table.columns:
                if col.category not in categories:
                    categories[col.category] = []
                categories[col.category].append(col.name)

            for category, cols in categories.items():
                summary += f"  {category}: {', '.join(cols)}\n"

            if table.relationships:
                summary += f"  Relationships: {len(table.relationships)}\n"

            summary += "\n"

        return summary
