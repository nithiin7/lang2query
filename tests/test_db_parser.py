"""Tests for the database parser module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from lang2query.utils.db_parser import Column, DatabaseSchema, MarkdownDBParser, Table


class TestColumn:
    """Test the Column dataclass."""

    def test_column_creation(self):
        """Test creating a Column instance."""
        column = Column(
            name="id",
            data_type="INT",
            nullable=False,
            key_type="PRIMARY KEY",
            description="Unique identifier",
            category="Identity",
        )

        assert column.name == "id"
        assert column.data_type == "INT"
        assert column.nullable is False
        assert column.key_type == "PRIMARY KEY"
        assert column.description == "Unique identifier"
        assert column.category == "Identity"


class TestTable:
    """Test the Table dataclass."""

    def test_table_creation(self):
        """Test creating a Table instance."""
        columns = [
            Column("id", "INT", False, "PRIMARY KEY", "Unique identifier", "Identity"),
            Column("name", "VARCHAR(50)", False, "-", "Table name", "Identity"),
        ]

        table = Table(
            name="test_table",
            columns=columns,
            relationships=["test_table (1) → (N) other_table"],
        )

        assert table.name == "test_table"
        assert len(table.columns) == 2
        assert len(table.relationships) == 1


class TestDatabaseSchema:
    """Test the DatabaseSchema dataclass."""

    def test_schema_creation(self):
        """Test creating a DatabaseSchema instance."""
        tables = {"users": Table("users", [], []), "orders": Table("orders", [], [])}
        notes = ["All tables use auto-incrementing primary keys"]

        schema = DatabaseSchema(tables=tables, notes=notes)

        assert len(schema.tables) == 2
        assert len(schema.notes) == 1
        assert "users" in schema.tables
        assert "orders" in schema.tables


class TestMarkdownDBParser:
    """Test the MarkdownDBParser class."""

    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = MarkdownDBParser("test_file.md")
        assert parser.file_path == Path("test_file.md")

    def test_parse_tables(self):
        """Test parsing table definitions from markdown."""
        parser = MarkdownDBParser("dummy.md")

        content = """
### users
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Unique identifier | Identity |
| name | VARCHAR(50) | NOT NULL | - | User name | Identity |

### orders
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Order ID | Identity |
"""

        tables = parser._parse_tables(content)

        assert len(tables) == 2
        assert "users" in tables
        assert "orders" in tables
        assert len(tables["users"].columns) == 2
        assert len(tables["orders"].columns) == 1

    def test_parse_columns(self):
        """Test parsing column definitions."""
        parser = MarkdownDBParser("dummy.md")

        table_content = """
| id | INT | NOT NULL | PRIMARY KEY | Unique identifier | Identity |
| name | VARCHAR(50) | NOT NULL | - | User name | Identity |
"""

        columns = parser._parse_columns(table_content)

        assert len(columns) == 2
        assert columns[0].name == "id"
        assert columns[0].data_type == "INT"
        assert columns[0].nullable is True
        assert columns[0].key_type == "PRIMARY KEY"
        assert columns[1].name == "name"
        assert columns[1].data_type == "VARCHAR(50)"

    def test_parse_relationships(self):
        """Test parsing table relationships."""
        parser = MarkdownDBParser("dummy.md")

        content = """
## Relationships
- users (1) → (N) orders
- orders (1) → (N) order_items
"""

        relationships = parser._parse_relationships(content)

        assert "users" in relationships
        assert "orders" in relationships
        assert "order_items" in relationships
        assert len(relationships["users"]) == 1
        assert len(relationships["orders"]) == 2

    def test_parse_notes(self):
        """Test parsing notes section."""
        parser = MarkdownDBParser("dummy.md")

        content = """
## Notes
- All tables use auto-incrementing primary keys
- Timestamps are in UTC
"""

        notes = parser._parse_notes(content)

        assert len(notes) == 2
        assert "All tables use auto-incrementing primary keys" in notes
        assert "Timestamps are in UTC" in notes

    def test_get_schema_summary(self):
        """Test generating schema summary."""
        parser = MarkdownDBParser("dummy.md")

        # Mock the parse method to return a test schema
        test_schema = DatabaseSchema(
            tables={
                "users": Table(
                    "users",
                    [
                        Column(
                            "id",
                            "INT",
                            False,
                            "PRIMARY KEY",
                            "Unique identifier",
                            "Identity",
                        ),
                        Column(
                            "name", "VARCHAR(50)", False, "-", "User name", "Identity"
                        ),
                    ],
                    [],
                ),
                "orders": Table(
                    "orders",
                    [Column("id", "INT", False, "PRIMARY KEY", "Order ID", "Identity")],
                    [],
                ),
            },
            notes=["Test note"],
        )

        with patch.object(parser, "parse", return_value=test_schema):
            summary = parser.get_schema_summary()

            assert "Table: users" in summary
            assert "Table: orders" in summary
            assert "Columns: 2" in summary
            assert "Columns: 1" in summary
            assert "Identity: id, name" in summary

    def test_file_not_found_error(self):
        """Test error handling for missing file."""
        parser = MarkdownDBParser("nonexistent.md")

        with pytest.raises(FileNotFoundError):
            parser.parse()
