"""
Read-only retriever over the SQL Knowledge Base ChromaDB collection written
by create_sql_kb_embeddings.py. Exposes the query methods that
tools/retriever_tools.py's LangChain @tool functions call into.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
import torch
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from retriever.embedding_utils import BGE_M3_EmbeddingFunction

# Matches a column content line built by
# SQLKnowledgeBaseChunker._create_table_columns_chunk, e.g.:
#   "email VARCHAR(100) uni no User's email address Contact"
# name and data_type are always present and space-free; key/nullable are
# optional and drawn from a fixed vocabulary so they're safely matched by
# keyword. Whatever text remains is [description] [category] - category is
# assumed to be the trailing single word (matches the source data, which
# uses single-word categories like "Primary"/"Authentication"/"Personal");
# everything before it is treated as description. This is a best-effort
# reconstruction of the original table row, not a lossless one - it's
# parsing free text that was joined with plain spaces and no delimiters.
_COLUMN_LINE_RE = re.compile(
    r"^(?P<name>\S+)\s+(?P<data_type>\S+)"
    r"(?:\s+(?P<key>pri|uni|mul))?"
    r"(?:\s+(?P<nullable>yes|no))?"
    r"(?:\s+(?P<rest>.+))?$"
)


class SQLKnowledgeBaseRetriever:
    """Read-only query interface over an existing SQL Knowledge Base collection"""

    def __init__(
        self,
        model_path: str = None,
        chroma_persist_dir: str = "./src/kb",
        collection_name: str = "sql_generation_kb",
    ):
        """
        Connect to the BGE-M3 model and the ChromaDB collection previously
        populated by SQLKnowledgeBaseEmbedder.

        Args:
            model_path: Path to local BGE-M3 model
            chroma_persist_dir: Directory the ChromaDB collection is persisted in
            collection_name: Name of the ChromaDB collection to query
        """
        if model_path is None:
            model_path = str(Path(__file__).parent.parent.parent / "models" / "bge-m3")

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"

        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. Please ensure BGE-M3 is downloaded."
            )
        self.model = SentenceTransformer(model_path, device=self.device)

        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_dir, settings=Settings(anonymized_telemetry=False)
        )

        self.collection_name = collection_name
        embedding_function = BGE_M3_EmbeddingFunction(self.model)
        try:
            self.collection = self.chroma_client.get_collection(
                name=collection_name, embedding_function=embedding_function
            )
        except Exception as e:
            raise RuntimeError(
                f"Collection '{collection_name}' not found at '{chroma_persist_dir}'. "
                f"Run the ingestion pipeline (create_sql_kb_embeddings.py) first."
            ) from e

    # ------------------------------------------------------------------
    # Semantic search (ChromaDB collection.query - ANN, ranked by relevance)
    # ------------------------------------------------------------------

    def semantic_search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        return self.collection.query(query_texts=[query], n_results=n_results)

    def search_by_chunk_type(
        self, query: str, chunk_type: str, n_results: int = 5
    ) -> Dict[str, Any]:
        return self.collection.query(
            query_texts=[query], n_results=n_results, where={"chunk_type": chunk_type}
        )

    def search_by_database(
        self, query: str, database_name: str, n_results: int = 5
    ) -> Dict[str, Any]:
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"database_name": database_name},
        )

    def search_by_table(
        self, query: str, database_name: str, table_name: str, n_results: int = 5
    ) -> Dict[str, Any]:
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={
                "$and": [{"database_name": database_name}, {"table_name": table_name}]
            },
        )

    def search_tables_in_databases(
        self, query: str, database_names: List[str], n_results: int = 5
    ) -> Dict[str, Any]:
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={
                "$and": [
                    {"chunk_type": "table"},
                    {"database_name": {"$in": database_names}},
                ]
            },
        )

    def complex_filter_search(
        self, query: str, filters: Dict[str, Any], n_results: int = 5
    ) -> Dict[str, Any]:
        return self.collection.query(
            query_texts=[query], n_results=n_results, where=filters
        )

    # ------------------------------------------------------------------
    # Enumeration (ChromaDB collection.get - deterministic metadata scan,
    # no embedding involved - correct for "list/count everything", where
    # ANN top-k would offer no completeness guarantee)
    # ------------------------------------------------------------------

    def get_all_databases(self) -> List[Dict[str, Any]]:
        result = self.collection.get(
            where={"chunk_type": "database"}, include=["metadatas", "documents"]
        )
        databases = []
        for metadata, document in zip(
            result.get("metadatas", []), result.get("documents", [])
        ):
            databases.append(
                {
                    "database": metadata.get("database_name"),
                    "system_name": metadata.get("system_name"),
                    "module_name": metadata.get("module_name"),
                    "purpose": self._extract_field(document, "Purpose:"),
                }
            )
        return databases

    def count_databases(self) -> int:
        result = self.collection.get(where={"chunk_type": "database"}, include=[])
        return len(result.get("ids", []))

    def get_tables_in_database(self, database_name: str) -> List[Dict[str, Any]]:
        result = self.collection.get(
            where={"$and": [{"chunk_type": "table"}, {"database_name": database_name}]},
            include=["metadatas", "documents"],
        )
        tables = []
        for metadata, document in zip(
            result.get("metadatas", []), result.get("documents", [])
        ):
            tables.append(
                {
                    "table": metadata.get("table_name"),
                    "purpose": self._extract_field(document, "Purpose:"),
                    "primary_keys": self._split_metadata_list(
                        metadata.get("primary_keys")
                    ),
                    "unique_keys": self._split_metadata_list(
                        metadata.get("unique_keys")
                    ),
                }
            )
        return tables

    def count_tables_in_database(self, database_name: str) -> int:
        result = self.collection.get(
            where={"$and": [{"chunk_type": "table"}, {"database_name": database_name}]},
            include=[],
        )
        return len(result.get("ids", []))

    def get_columns_by_table(
        self, database_name: str, table_names: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        result = self.collection.get(
            where={
                "$and": [
                    {"chunk_type": "column"},
                    {"database_name": database_name},
                    {"table_name": {"$in": table_names}},
                ]
            },
            include=["metadatas", "documents"],
        )

        table_columns: Dict[str, List[Dict[str, Any]]] = {}
        for metadata, document in zip(
            result.get("metadatas", []), result.get("documents", [])
        ):
            table_name = metadata.get("table_name")
            table_columns[table_name] = self._parse_column_lines(document)

        # Tables that exist but had no matching column chunk still get an
        # (empty) entry so callers can distinguish "no columns found" from
        # "table not requested".
        for table_name in table_names:
            table_columns.setdefault(table_name, [])

        return table_columns

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_field(content: str, prefix: str) -> Optional[str]:
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return None

    @staticmethod
    def _split_metadata_list(value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [v for v in value.split(",") if v]

    @staticmethod
    def _parse_column_lines(content: str) -> List[Dict[str, Any]]:
        columns = []
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("Table:") or line.startswith("Purpose:"):
                continue

            match = _COLUMN_LINE_RE.match(line)
            if not match:
                continue

            key = match.group("key")
            nullable = match.group("nullable")
            rest = (match.group("rest") or "").strip()

            description = None
            category = None
            if rest:
                tokens = rest.split(" ")
                if len(tokens) >= 2:
                    category = tokens[-1]
                    description = " ".join(tokens[:-1])
                else:
                    description = rest

            columns.append(
                {
                    "column_name": match.group("name"),
                    "data_type": match.group("data_type"),
                    "key_type": key.upper() if key else None,
                    "nullable": (nullable == "yes") if nullable else None,
                    "description": description,
                    "category": category,
                    # Not captured anywhere in the ingestion pipeline (chunker
                    # only parses name/data_type/key/null/description/category
                    # from source markdown) - always None, not a parsing gap.
                    "default_value": None,
                    "extra": None,
                }
            )
        return columns
