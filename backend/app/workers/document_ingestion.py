import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import chromadb
import torch
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.embedding_utils import BGE_M3_EmbeddingFunction
from ai.kb_chunker import KnowledgeBaseChunker


class DocumentIngestionPipeline:
    """Creates embeddings for a Knowledge Base using BGE-M3 and ChromaDB"""

    def __init__(
        self,
        model_path: str = None,
        chroma_persist_dir: str = "./ai/kb",
        collection_name: str = "knowledge_base",
    ):
        """
        Initialize the embedder with BGE-M3 and ChromaDB

        Args:
            model_path: Path to local BGE-M3 model
            chroma_persist_dir: Directory to persist ChromaDB
            collection_name: Name of the ChromaDB collection
        """
        # Set default model path
        if model_path is None:
            model_path = str(
                Path(__file__).resolve().parent.parent.parent.parent
                / "models"
                / "bge-m3"
            )

        # Detect and set device for MPS optimization on M1 Macs
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"

        print(f"Using device: {self.device}")
        print(f"Loading BGE-M3 model")

        # Load model with device optimization
        if Path(model_path).exists():
            self.model = SentenceTransformer(model_path, device=self.device)
            print(
                "Model loaded from local cache with MPS optimization"
                if self.device == "mps"
                else "Model loaded from local cache"
            )
        else:
            raise FileNotFoundError(
                f"Model not found at {model_path}. Please ensure BGE-M3 is downloaded."
            )

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_dir, settings=Settings(anonymized_telemetry=False)
        )
        print(f"ChromaDB initialized at: {chroma_persist_dir}")

        self.collection_name = collection_name
        self.chunker = KnowledgeBaseChunker()

    def create_or_get_collection(self, reset: bool = False):
        """Get the ChromaDB collection, creating it if absent (or recreating it if reset).

        Args:
            reset: If True, delete any existing collection with this name first.

        Returns:
            The ChromaDB collection, ready for chunk insertion.
        """
        embedding_function = BGE_M3_EmbeddingFunction(self.model)

        if reset:
            # Delete existing collection if reset
            try:
                self.chroma_client.delete_collection(name=self.collection_name)
                print(f" Deleted existing collection: {self.collection_name}")
            except Exception:
                pass

        try:
            collection = self.chroma_client.get_collection(
                name=self.collection_name, embedding_function=embedding_function
            )
            print(f"Using existing collection: {self.collection_name}")
            # Get count of existing documents
            count = collection.count()
            print(f"Existing documents in collection: {count}")
        except Exception:
            # Create new collection
            collection = self.chroma_client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                metadata={
                    "description": "Knowledge Base with BGE-M3 embeddings",
                    "created_at": datetime.now().isoformat(),
                    "embedding_model": "BAAI/bge-m3",
                    "chunk_strategy": "contextual_v2",
                },
            )
            print(f"Created new collection: {self.collection_name}")

        return collection

    def _adaptive_batch_size(self, chunks: List, batch_size: int) -> int:
        """Shrink the batch size for large chunks to avoid memory spikes."""
        if batch_size <= 1 or not chunks:
            return batch_size

        avg_chunk_size = sum(len(c.content) for c in chunks) / len(chunks)
        if avg_chunk_size > 5000:  # Very large chunks
            adaptive_batch_size = 1
        elif avg_chunk_size > 2000:  # Large chunks
            adaptive_batch_size = max(1, batch_size // 2)
        else:
            adaptive_batch_size = batch_size

        if adaptive_batch_size != batch_size:
            print(
                f"Avg chunk size {avg_chunk_size:.0f} chars, reducing batch size to {adaptive_batch_size}"
            )
        return adaptive_batch_size

    def _dedupe_batch(self, batch: List) -> List:
        """Drop duplicate chunk_ids within a single batch."""
        seen_ids = set()
        unique = []
        for c in batch:
            if c.chunk_id in seen_ids:
                continue
            seen_ids.add(c.chunk_id)
            unique.append(c)
        return unique

    def _filter_new(self, batch: List, collection) -> List:
        """Drop chunks whose ids already exist in the collection."""
        ids = [c.chunk_id for c in batch]
        try:
            existing = collection.get(ids=ids)
            existing_ids = set(existing.get("ids", [])) if existing else set()
        except Exception:
            existing_ids = set()
        return [c for c in batch if c.chunk_id not in existing_ids]

    def _normalize_metadata(self, chunk) -> Dict[str, Any]:
        """Flatten a chunk's metadata into ChromaDB-compatible scalar values.

        List values are joined into comma-separated strings, since ChromaDB
        metadata values must be scalars.
        """
        metadata = {
            k: (",".join(str(x) for x in v) if isinstance(v, list) else v)
            for k, v in chunk.metadata.items()
        }
        metadata["chunk_type"] = chunk.chunk_type
        return metadata

    def _add_batch(self, collection, batch: List, batch_num: int) -> None:
        """Add a batch to the collection, falling back to one-by-one on failure."""
        documents = [c.content for c in batch]
        metadatas = [self._normalize_metadata(c) for c in batch]
        ids = [c.chunk_id for c in batch]

        try:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            return
        except Exception as e:
            print(f"\nError embedding batch {batch_num}: {str(e)}")
            print(f"   Batch contains {len(batch)} chunks:")
            for c in batch[:5]:
                print(f"     - {c.chunk_id} (content size: {len(c.content)} chars)")
            if len(batch) > 5:
                print(f"     ... and {len(batch) - 5} more chunks")

        # Best-effort: retry one chunk at a time, skipping conflicts
        failed_count = 0
        for idx, c in enumerate(batch):
            try:
                collection.add(
                    documents=[c.content], metadatas=[metadatas[idx]], ids=[c.chunk_id]
                )
            except Exception as inner_e:
                failed_count += 1
                if failed_count <= 3:  # Only print first few errors
                    print(f"   Failed to add chunk {c.chunk_id}: {str(inner_e)}")
        if failed_count:
            print(f"    Failed to add {failed_count} chunks from batch {batch_num}")

    def embed_chunks(self, chunks: List, collection, batch_size: int = 5):
        """Embed chunks and store in ChromaDB, skipping ids already present."""
        print(f"\nCreating embeddings for {len(chunks)} chunks...")

        adaptive_batch_size = self._adaptive_batch_size(chunks, batch_size)
        total_batches = (len(chunks) + adaptive_batch_size - 1) // adaptive_batch_size

        for i in tqdm(
            range(0, len(chunks), adaptive_batch_size),
            desc="Embedding batches",
            total=total_batches,
        ):
            batch = self._dedupe_batch(chunks[i : i + adaptive_batch_size])
            if not batch:
                continue

            batch = self._filter_new(batch, collection)
            if not batch:
                continue

            self._add_batch(collection, batch, batch_num=i // adaptive_batch_size + 1)

        print(
            f"\nSuccessfully embedded chunks into collection '{self.collection_name}'"
        )

    def verify_embeddings(self, collection, sample_queries: List[str] = None):
        """Verify embeddings with sample queries"""
        print("\nVerifying embeddings with sample queries...")

        if sample_queries is None:
            sample_queries = [
                "transaction tables in aeps database",
                "audit table columns",
                "card token system purpose",
                "primary keys in visa_merchant_mapping",
            ]

        for query in sample_queries:
            print(f"\nQuery: '{query}'")

            try:
                results = collection.query(query_texts=[query], n_results=3)

                if results["documents"][0]:
                    for i, (doc, distance, metadata, chunk_id) in enumerate(
                        zip(
                            results["documents"][0],
                            results["distances"][0],
                            results["metadatas"][0],
                            results["ids"][0],
                        )
                    ):
                        print(f"\n   Result {i+1}:")
                        print(f"   - Chunk ID: {chunk_id}")
                        print(f"   - Distance: {distance:.4f}")
                        print(f"   - Type: {metadata.get('chunk_type', 'unknown')}")
                        print(
                            f"   - Database: {metadata.get('database_name', 'unknown')}"
                        )
                        if "table_name" in metadata:
                            print(f"   - Table: {metadata['table_name']}")
                        print(f"   - Content preview: {doc[:150]}...")
                else:
                    print("   No results found")

            except Exception as e:
                print(f"   Error: {str(e)}")

    def save_metadata(
        self,
        stats: Dict[str, Any],
        output_file: str = "ai/output/kb_metadata.json",
    ):
        """Save metadata about the knowledge base using pre-aggregated stats"""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "total_chunks": int(stats.get("total_chunks", 0)),
            "chunk_types": {
                "database": int(stats.get("database", 0)),
                "table": int(stats.get("table", 0)),
                "column": int(stats.get("column", 0)),
            },
            "databases": sorted(list(stats.get("databases", set()))),
            "modules": sorted(list(stats.get("modules", set()))),
            "collection_name": self.collection_name,
            "embedding_model": "BAAI/bge-m3",
            "chunk_strategy": "contextual_v2",
        }

        with open(output_file, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"\nSaved knowledge base metadata to {output_file}")

    def embed_markdown_directory_streaming(
        self,
        md_directory: str,
        collection,
        batch_size: int = 5,
        test_only: bool = False,
        per_file_output_dir: str = None,
        per_file_chunked_json_dir: str = None,
    ):
        """Stream-process markdown files: chunk, embed, and discard per file to minimize memory.

        Returns a tuple of (stats, parsing_errors).
        stats keys: total_chunks, database, table, column, databases (set), modules (set).
        """
        md_path = Path(md_directory)
        if not md_path.exists():
            raise FileNotFoundError(f"Directory not found: {md_directory}")

        md_files = list(md_path.glob("*.md"))
        if test_only:
            md_files = md_files[:3]

        print(f"\nFound {len(md_files)} markdown files to process (streaming mode)")

        # Prepare optional output directories for per-file JSON dumps
        if per_file_output_dir:
            Path(per_file_output_dir).mkdir(parents=True, exist_ok=True)
        if per_file_chunked_json_dir:
            Path(per_file_chunked_json_dir).mkdir(parents=True, exist_ok=True)

        stats = {
            "total_chunks": 0,
            "database": 0,
            "table": 0,
            "column": 0,
            "databases": set(),
            "modules": set(),
        }
        parsing_errors: List[str] = []

        for md_file in tqdm(md_files, desc="Streaming files"):
            try:
                chunks = self.chunker.parse_markdown_file(str(md_file))
                if not chunks:
                    continue

                # Update stats before embedding
                stats["total_chunks"] += len(chunks)
                for c in chunks:
                    if c.chunk_type in ("database", "table", "column"):
                        stats[c.chunk_type] += 1
                    db_name = c.metadata.get("database_name")
                    if db_name:
                        stats["databases"].add(db_name)
                    module_name = c.metadata.get("module_name")
                    if module_name:
                        stats["modules"].add(module_name)

                # Save per-file chunks JSON to requested folders (reuse chunker's utility)
                base_name = md_file.stem
                if per_file_output_dir:
                    out_path = Path(per_file_output_dir) / f"{base_name}_chunks_v2.json"
                    self.chunker.save_chunks_to_json(chunks, str(out_path))
                if per_file_chunked_json_dir:
                    out_path2 = (
                        Path(per_file_chunked_json_dir) / f"{base_name}_chunks_v2.json"
                    )
                    self.chunker.save_chunks_to_json(chunks, str(out_path2))

                # Embed and free per file
                self.embed_chunks(chunks, collection, batch_size=batch_size)

                # Explicitly drop reference to chunks to free memory earlier
                del chunks
            except Exception as e:
                error_msg = f"Error processing {md_file.name}: {str(e)}"
                parsing_errors.append(error_msg)
                print(f"\n{error_msg}")

        # Print brief statistics summary
        print("\nChunk Statistics (streaming):")
        print(f"   - Total chunks: {stats['total_chunks']}")
        print(f"   - Database info chunks: {stats['database']}")
        print(f"   - Table summary chunks: {stats['table']}")
        print(f"   - Table columns chunks: {stats['column']}")
        print(f"   - Unique databases: {len(stats['databases'])}")
        print(f"   - Unique modules: {len(stats['modules'])}")

        if parsing_errors:
            print(f"\n Encountered {len(parsing_errors)} parsing errors (streaming):")
            for error in parsing_errors[:5]:
                print(f"   - {error}")
            if len(parsing_errors) > 5:
                print(f"   ... and {len(parsing_errors) - 5} more errors")

        return stats, parsing_errors


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the ingestion pipeline entrypoint."""
    parser = argparse.ArgumentParser(description="Create Knowledge Base embeddings")
    parser.add_argument(
        "--md-dir",
        type=str,
        default="input",
        help="Directory containing markdown files",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path to BGE-M3 model (default: models/bge-m3)",
    )
    parser.add_argument(
        "--chroma-dir",
        type=str,
        default="./ai/kb",
        help="Directory for ChromaDB persistence",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="knowledge_base",
        help="Name of ChromaDB collection",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Batch size for embedding (default: 3, use 1 for max memory safety)",
    )
    parser.add_argument(
        "--single-chunk",
        action="store_true",
        help="Force single chunk processing (batch-size=1, maximum memory safety)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset existing collection before embedding",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only process first 3 files for testing",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="ai/output",
        help="Directory to save per-file chunks JSON copies",
    )
    parser.add_argument(
        "--chunked-json-dir",
        type=str,
        default="ai/output",
        help="Directory to save per-file chunks JSON copies (secondary)",
    )

    args = parser.parse_args()

    if args.single_chunk:
        args.batch_size = 1
        print("Single-chunk mode enabled (maximum memory safety)")

    return args


def main():
    """Main function to create Knowledge Base embeddings"""
    args = _parse_args()

    print("Knowledge Base Embedding Creation")
    print("=" * 60)
    print(f"Markdown directory: {args.md_dir}")
    print(f"ChromaDB directory: {args.chroma_dir}")
    print(f"Collection name: {args.collection_name}")
    print(f"Reset collection: {args.reset}")
    print(f"Test mode: {args.test_only}")
    print(f"Batch size: {args.batch_size}")
    print("=" * 60)

    pipeline = DocumentIngestionPipeline(
        model_path=args.model_path,
        chroma_persist_dir=args.chroma_dir,
        collection_name=args.collection_name,
    )

    collection = pipeline.create_or_get_collection(reset=args.reset)

    # Stream-process markdown files to avoid holding all chunks in memory
    stats, parsing_errors = pipeline.embed_markdown_directory_streaming(
        args.md_dir,
        collection,
        batch_size=args.batch_size,
        test_only=args.test_only,
        per_file_output_dir=args.output_dir,
        per_file_chunked_json_dir=args.chunked_json_dir,
    )

    if stats.get("total_chunks", 0) == 0:
        print("\nNo chunks created. Please check your markdown files.")
        return

    pipeline.save_metadata(stats)
    pipeline.verify_embeddings(collection)

    print("\nKnowledge Base embedding creation completed!")
    print(f"Total documents in collection: {collection.count()}")


if __name__ == "__main__":
    main()
