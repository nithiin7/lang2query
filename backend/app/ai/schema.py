"""
Knowledge Base Chunk Schemas

Dataclasses for the three levels of documentation chunk produced by
KnowledgeBaseChunker (database / table / column) and persisted to ChromaDB.
"""

from dataclasses import dataclass
from typing import Any, Dict, Literal


class _ChunkDictMixin:
    """Shared `to_dict` for chunk dataclasses. No fields of its own, so it's
    safe to mix into a dataclass without disturbing field ordering."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the chunk to a ChromaDB-ready dict (chunk_id/content/metadata).

        Returns:
            Dict with metadata guaranteed to include a `chunk_type` key.
        """
        metadata = dict(self.metadata)
        if "chunk_type" not in metadata:
            metadata["chunk_type"] = self.chunk_type
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": metadata,
        }


@dataclass
class DatabaseChunk(_ChunkDictMixin):
    """Represents a database-level chunk of documentation"""

    chunk_id: str
    chunk_type: Literal["database"]
    content: str
    metadata: Dict[str, Any]


@dataclass
class TableChunk(_ChunkDictMixin):
    """Represents a table-level chunk of documentation"""

    chunk_id: str
    chunk_type: Literal["table"]
    content: str
    metadata: Dict[str, Any]


@dataclass
class ColumnChunk(_ChunkDictMixin):
    """Represents a column-level chunk of documentation"""

    chunk_id: str
    chunk_type: Literal["column"]
    content: str
    metadata: Dict[str, Any]
