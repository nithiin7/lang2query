"""
Utility to load database, table, and column metadata from chunk JSON files in docs/.

Expected chunk shapes (abbreviated):
- database_info: metadata.database_name, content with Purpose
- table_summary: metadata.database_name, table_name, content with Purpose
- table_columns: metadata.database_name, table_name, content with columns in hyphen-list
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ColumnSchema:
    name: str
    data_type: Optional[str] = None
    is_primary_key: bool = False
    is_unique: bool = False
    is_indexed: bool = False


@dataclass
class TableSchema:
    name: str
    purpose: str = ""
    columns: List[ColumnSchema] = field(default_factory=list)


@dataclass
class DatabaseSchema:
    name: str
    system: Optional[str] = None
    module: Optional[str] = None
    purpose: str = ""
    tables: Dict[str, TableSchema] = field(default_factory=dict)


class ChunksLoader:
    """Aggregates schemas from chunk JSON files in a directory."""

    def __init__(self, docs_dir: str):
        self.docs_dir = docs_dir
        self.databases: Dict[str, DatabaseSchema] = {}

    def load(self) -> None:
        if not os.path.isdir(self.docs_dir):
            return

        for entry in os.listdir(self.docs_dir):
            if not entry.lower().endswith(".json"):
                continue
            abs_path = os.path.join(self.docs_dir, entry)
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for chunk in data:
                        self._ingest_chunk(chunk)
            except Exception:
                # Ignore malformed files; caller can inspect loaded content
                continue

    def _ensure_db(self, db_name: str) -> DatabaseSchema:
        if db_name not in self.databases:
            self.databases[db_name] = DatabaseSchema(name=db_name)
        return self.databases[db_name]

    def _ingest_chunk(self, chunk: dict) -> None:
        ctype = (
            chunk.get("chunk_type") or chunk.get("metadata", {}).get("chunk_type") or ""
        ).strip()
        meta = chunk.get("metadata", {})
        content = chunk.get("content", "") or ""

        if ctype == "database_info":
            db = self._ensure_db(meta.get("database_name", ""))
            db.system = meta.get("system_name")
            db.module = meta.get("module_name")
            # Try to extract Purpose: line
            purpose = _extract_after_prefix(content, "Purpose:")
            db.purpose = purpose or db.purpose
            return

        if ctype == "table_summary":
            db = self._ensure_db(meta.get("database_name", ""))
            table_name = meta.get("table_name", "")
            if not table_name:
                return
            table = db.tables.get(table_name) or TableSchema(name=table_name)
            table.purpose = _extract_after_prefix(content, "Purpose:") or table.purpose
            db.tables[table_name] = table
            return

        if ctype == "table_columns":
            db = self._ensure_db(meta.get("database_name", ""))
            table_name = meta.get("table_name", "")
            if not table_name:
                return
            table = db.tables.get(table_name) or TableSchema(name=table_name)

            # Parse hyphen lines such as: "- id (bigint(20), PRI): NO"
            primary_keys = set(meta.get("primary_keys", []) or [])
            unique_cols = set(meta.get("unique_columns", []) or [])
            indexed_cols = set(meta.get("indexed_columns", []) or [])

            parsed_columns: List[ColumnSchema] = []
            for line in content.splitlines():
                line = line.strip()
                if not line.startswith("- "):
                    continue
                # Remove leading "- "
                body = line[2:]
                # Expect formats like: "name (type, FLAG): X"
                name_part, type_part = _split_before("(", body)
                col_name = name_part.strip().rstrip(":")
                dtype = None
                if type_part:
                    # Up to ")"
                    dtype = type_part.split(")", 1)[0].strip()
                    # If there are multiple comma-separated values, first is datatype
                    if "," in dtype:
                        dtype = dtype.split(",", 1)[0].strip()
                parsed_columns.append(
                    ColumnSchema(
                        name=col_name,
                        data_type=dtype if dtype else None,
                        is_primary_key=col_name in primary_keys,
                        is_unique=col_name in unique_cols,
                        is_indexed=col_name in indexed_cols,
                    )
                )

            if parsed_columns:
                table.columns = parsed_columns
            db.tables[table_name] = table
            return

    # Convenience accessors
    def database_names(self) -> List[str]:
        return list(self.databases.keys())

    def database_descriptions(self) -> Dict[str, str]:
        desc: Dict[str, str] = {}
        for name, db in self.databases.items():
            if db.purpose:
                desc[name] = db.purpose
            else:
                desc[name] = (
                    f"System: {db.system or ''} Module: {db.module or ''}".strip()
                )
        return desc

    def available_tables(self, db_names: List[str]) -> List[Dict[str, str]]:
        tables_info = []
        for db_name in db_names:
            db = self.databases.get(db_name)
            if not db:
                continue
            for tname, table in db.tables.items():
                desc = table.purpose or ""
                cols_preview = ", ".join(
                    [
                        f"{c.name}{f' ({c.data_type})' if c.data_type else ''}"
                        for c in (table.columns or [])
                    ][:15]
                )
                table_info = {
                    "name": tname,
                    "description": desc,
                    "columns": cols_preview,
                    "database": db_name,
                }
                tables_info.append(table_info)
        return tables_info

    def get_table_columns(
        self, table_names: List[str], db_names: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get detailed column information for specific tables.

        Args:
            table_names: List of table names to get columns for
            db_names: List of database names to search in

        Returns:
            Dictionary mapping table_name -> list of column info dictionaries
        """
        table_columns = {}

        for db_name in db_names:
            db = self.databases.get(db_name)
            if not db:
                continue

            for table_name in table_names:
                # Find table with case-insensitive matching
                found_table = None
                for existing_table_name in db.tables.keys():
                    if existing_table_name.lower() == table_name.lower():
                        found_table = db.tables[existing_table_name]
                        break

                if found_table:
                    columns_info = []

                    for col in found_table.columns:
                        col_info = {
                            "name": col.name,
                            "data_type": col.data_type or "unknown",
                            "is_primary_key": col.is_primary_key,
                            "is_unique": col.is_unique,
                            "is_indexed": col.is_indexed,
                        }
                        columns_info.append(col_info)

                    table_columns[table_name] = columns_info

        return table_columns


def _extract_after_prefix(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.strip().lower().startswith(prefix.lower()):
            return line.split(":", 1)[-1].strip()
    return ""


def _split_before(token: str, text: str):
    idx = text.find(token)
    if idx == -1:
        return text, ""
    return text[:idx], text[idx + 1 :]
