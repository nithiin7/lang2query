import os
import sys
import ssl
import warnings
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import argparse
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from src.retriever.sql_kb_chunker import SQLKnowledgeBaseChunker

# Add the parent directory to Python path to allow absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ssl._create_default_https_context = ssl._create_unverified_context
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class BGE_M3_EmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Custom embedding function for ChromaDB using BGE-M3"""
    
    def __init__(self, model):
        self.model = model
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(input, show_progress_bar=False)
        return embeddings.tolist()


class SQLKnowledgeBaseEmbedder:
    """Creates embeddings for SQL Knowledge Base using BGE-M3 and ChromaDB"""
    
    def __init__(self,
                 model_path: str = None,
                 chroma_persist_dir: str = "./src/kb",
                 collection_name: str = "sql_generation_kb"):
        """
        Initialize the embedder with BGE-M3 and ChromaDB

        Args:
            model_path: Path to local BGE-M3 model
            chroma_persist_dir: Directory to persist ChromaDB
            collection_name: Name of the ChromaDB collection
        """
        # Set default model path
        if model_path is None:
            model_path = str(Path(__file__).parent.parent.parent / "models" / "bge-m3")

        # Detect and set device for MPS optimization on M1 Macs
        self.device = 'mps' if torch.backends.mps.is_available() else 'cpu'

        print(f"🚀 Using device: {self.device}")
        print(f"🚀 Loading BGE-M3 model")

        # Load model with device optimization
        if Path(model_path).exists():
            self.model = SentenceTransformer(model_path, device=self.device)
            print("✅ Model loaded from local cache with MPS optimization" if self.device == 'mps' else "✅ Model loaded from local cache")
        else:
            raise FileNotFoundError(f"Model not found at {model_path}. Please ensure BGE-M3 is downloaded.")
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        print(f"✅ ChromaDB initialized at: {chroma_persist_dir}")
        
        self.collection_name = collection_name
        self.chunker = SQLKnowledgeBaseChunker()
        
    def create_or_get_collection(self, reset: bool = False):
        embedding_function = BGE_M3_EmbeddingFunction(self.model)
        
        if reset:
            # Delete existing collection if reset
            try:
                self.chroma_client.delete_collection(name=self.collection_name)
                print(f"🗑️  Deleted existing collection: {self.collection_name}")
            except:
                pass
        
        try:
            collection = self.chroma_client.get_collection(
                name=self.collection_name,
                embedding_function=embedding_function
            )
            print(f"✅ Using existing collection: {self.collection_name}")
            # Get count of existing documents
            count = collection.count()
            print(f"📊 Existing documents in collection: {count}")
        except:
            # Create new collection
            collection = self.chroma_client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                metadata={
                    "description": "SQL Generation Knowledge Base with BGE-M3 embeddings",
                    "created_at": datetime.now().isoformat(),
                    "embedding_model": "BAAI/bge-m3",
                    "chunk_strategy": "contextual_v2"
                }
            )
            print(f"✅ Created new collection: {self.collection_name}")
        
        return collection
    
    def process_markdown_files(self, md_directory: str, batch_size: int = 5):
        """Process all markdown files in the directory"""
        md_path = Path(md_directory)
        if not md_path.exists():
            raise FileNotFoundError(f"Directory not found: {md_directory}")
        
        # Get all markdown files
        md_files = list(md_path.glob("*.md"))
        print(f"\n📁 Found {len(md_files)} markdown files to process")
        
        all_chunks = []
        parsing_errors = []
        
        # Process each file
        print("\n🔍 Chunking markdown files...")
        for md_file in tqdm(md_files, desc="Processing files"):
            try:
                chunks = self.chunker.parse_markdown_file(str(md_file))
                all_chunks.extend(chunks)
            except Exception as e:
                error_msg = f"Error processing {md_file.name}: {str(e)}"
                parsing_errors.append(error_msg)
                print(f"\n❌ {error_msg}")
        
        print(f"\n✅ Created {len(all_chunks)} chunks from {len(md_files)} files")

        self._print_chunk_statistics(all_chunks)
        
        if parsing_errors:
            print(f"\n⚠️  Encountered {len(parsing_errors)} parsing errors:")
            for error in parsing_errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(parsing_errors) > 5:
                print(f"   ... and {len(parsing_errors) - 5} more errors")
        
        return all_chunks, parsing_errors
    
    def _print_chunk_statistics(self, chunks: List):
        db_chunks = [c for c in chunks if c.chunk_type == 'database']
        table_chunks = [c for c in chunks if c.chunk_type == 'table']
        column_chunks = [c for c in chunks if c.chunk_type == 'column']
        
        unique_dbs = set()
        unique_modules = set()
        for chunk in chunks:
            if 'database_name' in chunk.metadata:
                unique_dbs.add(chunk.metadata['database_name'])
            if 'module_name' in chunk.metadata:
                unique_modules.add(chunk.metadata['module_name'])
        
        print("\n📊 Chunk Statistics:")
        print(f"   - Total chunks: {len(chunks)}")
        print(f"   - Database info chunks: {len(db_chunks)}")
        print(f"   - Table summary chunks: {len(table_chunks)}")
        print(f"   - Table columns chunks: {len(column_chunks)}")
        print(f"   - Unique databases: {len(unique_dbs)}")
        print(f"   - Unique modules: {len(unique_modules)}")
    
    def embed_chunks(self, chunks: List, collection, batch_size: int = 5):
        """Embed chunks and store in ChromaDB with memory-aware batching"""
        print(f"\n🚀 Creating embeddings for {len(chunks)} chunks...")

        # Adaptive batch sizing based on content size
        if batch_size > 1:
            # Calculate average chunk size
            avg_chunk_size = sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0
            # Reduce batch size for large chunks to prevent memory issues
            if avg_chunk_size > 2000:  # Large chunks
                adaptive_batch_size = max(1, batch_size // 2)
                print(f"📊 Large chunks detected (avg {avg_chunk_size:.0f} chars), reducing batch size to {adaptive_batch_size}")
            elif avg_chunk_size > 5000:  # Very large chunks
                adaptive_batch_size = 1
                print(f"📊 Very large chunks detected (avg {avg_chunk_size:.0f} chars), using batch size 1")
            else:
                adaptive_batch_size = batch_size
        else:
            adaptive_batch_size = batch_size

        total_batches = (len(chunks) + adaptive_batch_size - 1) // adaptive_batch_size

        for i in tqdm(range(0, len(chunks), adaptive_batch_size), desc="Embedding batches", total=total_batches):
            batch = chunks[i:i + adaptive_batch_size]

            # Remove within-batch dup ids
            uniq = []
            seen_ids = set()
            for c in batch:
                if c.chunk_id in seen_ids:
                    continue
                seen_ids.add(c.chunk_id)
                uniq.append(c)
            batch = uniq
            if not batch:
                continue

            # Skip IDs that already exist in the collection
            ids = [c.chunk_id for c in batch]
            try:
                existing = collection.get(ids=ids)
                existing_ids = set(existing.get('ids', [])) if existing and existing.get('ids') else set()
            except Exception:
                existing_ids = set()

            batch = [c for c in batch if c.chunk_id not in existing_ids]
            if not batch:
                continue

            documents = [c.content for c in batch]

            processed_metadatas = []
            for c in batch:
                m = {}
                for k, v in c.metadata.items():
                    if isinstance(v, list):
                        m[k] = ','.join(str(x) for x in v)
                    else:
                        m[k] = v
                        
                m['chunk_type'] = c.chunk_type
                processed_metadatas.append(m)

            ids = [c.chunk_id for c in batch]

            try:
                collection.add(documents=documents, metadatas=processed_metadatas, ids=ids)
            except Exception as e:
                batch_num = i//adaptive_batch_size + 1
                print(f"\n❌ Error embedding batch {batch_num}: {str(e)}")
                print(f"   📋 Batch contains {len(batch)} chunks:")
                for c in batch[:5]:  # Show first 5 chunks
                    print(f"     - {c.chunk_id} (content size: {len(c.content)} chars)")
                if len(batch) > 5:
                    print(f"     ... and {len(batch) - 5} more chunks")

                # Best-effort: try to add one-by-one skipping conflicts
                failed_count = 0
                for idx, c in enumerate(batch):
                    try:
                        # Use the corresponding metadata from the same index
                        collection.add(documents=[c.content],
                                       metadatas=[processed_metadatas[idx]],
                                       ids=[c.chunk_id])
                    except Exception as inner_e:
                        failed_count += 1
                        if failed_count <= 3:  # Only print first few errors
                            print(f"   ❌ Failed to add chunk {c.chunk_id}: {str(inner_e)}")
                        continue
                if failed_count > 0:
                    print(f"   ⚠️  Failed to add {failed_count} chunks from batch {batch_num}")

        print(f"\n✅ Successfully embedded chunks into collection '{self.collection_name}'")
    
    def verify_embeddings(self, collection, sample_queries: List[str] = None):
        """Verify embeddings with sample queries"""
        print("\n🔍 Verifying embeddings with sample queries...")
        
        if sample_queries is None:
            sample_queries = [
                "transaction tables in aeps database",
                "audit table columns",
                "card token system purpose",
                "primary keys in visa_merchant_mapping"
            ]
        
        for query in sample_queries:
            print(f"\n📝 Query: '{query}'")
            
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=3
                )
                
                if results['documents'][0]:
                    for i, (doc, distance, metadata, chunk_id) in enumerate(zip(
                        results['documents'][0],
                        results['distances'][0],
                        results['metadatas'][0],
                        results['ids'][0]
                    )):
                        print(f"\n   Result {i+1}:")
                        print(f"   - Chunk ID: {chunk_id}")
                        print(f"   - Distance: {distance:.4f}")
                        print(f"   - Type: {metadata.get('chunk_type', 'unknown')}")
                        print(f"   - Database: {metadata.get('database_name', 'unknown')}")
                        if 'table_name' in metadata:
                            print(f"   - Table: {metadata['table_name']}")
                        print(f"   - Content preview: {doc[:150]}...")
                else:
                    print("   No results found")
                    
            except Exception as e:
                print(f"   Error: {str(e)}")
    
    def save_metadata(self, chunks: List, output_file: str = "src/retriever/output/sql_kb_metadata.json"):
        """Save metadata about the knowledge base"""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "total_chunks": len(chunks),
            "chunk_types": {
                "database": len([c for c in chunks if c.chunk_type == 'database']),
                "table": len([c for c in chunks if c.chunk_type == 'table']),
                "column": len([c for c in chunks if c.chunk_type == 'column'])
            },
            "databases": list(set(c.metadata.get('database_name', 'unknown') for c in chunks)),
            "modules": list(set(c.metadata.get('module_name', 'unknown') for c in chunks if 'module_name' in c.metadata)),
            "collection_name": self.collection_name,
            "embedding_model": "BAAI/bge-m3",
            "chunk_strategy": "contextual_v2"
        }
        
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n📄 Saved knowledge base metadata to {output_file}")

    def save_metadata_from_stats(self, stats: Dict[str, Any], output_file: str = "src/retriever/output/sql_kb_metadata.json"):
        """Save metadata using pre-aggregated stats to avoid holding all chunks in memory"""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "total_chunks": int(stats.get("total_chunks", 0)),
            "chunk_types": {
                "database": int(stats.get("database", 0)),
                "table": int(stats.get("table", 0)),
                "column": int(stats.get("column", 0))
            },
            "databases": sorted(list(stats.get("databases", set()))),
            "modules": sorted(list(stats.get("modules", set()))),
            "collection_name": self.collection_name,
            "embedding_model": "BAAI/bge-m3",
            "chunk_strategy": "contextual_v2"
        }

        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\n📄 Saved knowledge base metadata to {output_file}")

    def embed_markdown_directory_streaming(self, md_directory: str, collection, batch_size: int = 5, test_only: bool = False,
                                           per_file_output_dir: str = None, per_file_chunked_json_dir: str = None):
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

        print(f"\n📁 Found {len(md_files)} markdown files to process (streaming mode)")

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
                    out_path2 = Path(per_file_chunked_json_dir) / f"{base_name}_chunks_v2.json"
                    self.chunker.save_chunks_to_json(chunks, str(out_path2))

                # Embed and free per file
                self.embed_chunks(chunks, collection, batch_size=batch_size)

                # Explicitly drop reference to chunks to free memory earlier
                del chunks
            except Exception as e:
                error_msg = f"Error processing {md_file.name}: {str(e)}"
                parsing_errors.append(error_msg)
                print(f"\n❌ {error_msg}")

        # Print brief statistics summary
        print("\n📊 Chunk Statistics (streaming):")
        print(f"   - Total chunks: {stats['total_chunks']}")
        print(f"   - Database info chunks: {stats['database']}")
        print(f"   - Table summary chunks: {stats['table']}")
        print(f"   - Table columns chunks: {stats['column']}")
        print(f"   - Unique databases: {len(stats['databases'])}")
        print(f"   - Unique modules: {len(stats['modules'])}")

        if parsing_errors:
            print(f"\n⚠️  Encountered {len(parsing_errors)} parsing errors (streaming):")
            for error in parsing_errors[:5]:
                print(f"   - {error}")
            if len(parsing_errors) > 5:
                print(f"   ... and {len(parsing_errors) - 5} more errors")

        return stats, parsing_errors

    def _deduplicate_chunks(self, chunks):
        seen = set()
        unique = []
        dup_count = 0
        for c in chunks:
            if c.chunk_id in seen:
                dup_count += 1
                continue
            seen.add(c.chunk_id)
            unique.append(c)
        if dup_count:
            print(f"⚠️  Deduped {dup_count} duplicate chunks (by chunk_id)")
        return unique


def main():
    """Main function to create SQL KB embeddings"""
    parser = argparse.ArgumentParser(description="Create SQL Knowledge Base embeddings")
    parser.add_argument("--md-dir", type=str, default="input",
                       help="Directory containing markdown files")
    parser.add_argument("--model-path", type=str, default=None,
                       help="Path to BGE-M3 model (default: models/bge-m3)")
    parser.add_argument("--chroma-dir", type=str, default="./src/kb",
                       help="Directory for ChromaDB persistence")
    parser.add_argument("--collection-name", type=str, default="sql_generation_kb",
                       help="Name of ChromaDB collection")
    parser.add_argument("--batch-size", type=int, default=3,
                       help="Batch size for embedding (default: 3, use 1 for max memory safety)")
    parser.add_argument("--single-chunk", action="store_true",
                       help="Force single chunk processing (batch-size=1, maximum memory safety)")
    parser.add_argument("--reset", action="store_true",
                       help="Reset existing collection before embedding")
    parser.add_argument("--test-only", action="store_true",
                       help="Only process first 3 files for testing")
    parser.add_argument("--output-dir", type=str, default="src/retriever/output",
                       help="Directory to save per-file chunks JSON copies")
    parser.add_argument("--chunked-json-dir", type=str, default="src/retriever/output",
                       help="Directory to save per-file chunks JSON copies (secondary)")
    
    args = parser.parse_args()

    # Handle single-chunk option
    if args.single_chunk:
        args.batch_size = 1
        print("🔒 Single-chunk mode enabled (maximum memory safety)")

    print("🚀 SQL Knowledge Base Embedding Creation")
    print("=" * 60)
    print(f"📁 Markdown directory: {args.md_dir}")
    print(f"💾 ChromaDB directory: {args.chroma_dir}")
    print(f"📚 Collection name: {args.collection_name}")
    print(f"🔄 Reset collection: {args.reset}")
    print(f"🧪 Test mode: {args.test_only}")
    print(f"📦 Batch size: {args.batch_size}")
    print("=" * 60)
    
    # Initialize embedder
    embedder = SQLKnowledgeBaseEmbedder(
        model_path=args.model_path,
        chroma_persist_dir=args.chroma_dir,
        collection_name=args.collection_name
    )
    
    # Create or get collection
    collection = embedder.create_or_get_collection(reset=args.reset)
    
    # Stream-process markdown files to avoid holding all chunks in memory
    stats, parsing_errors = embedder.embed_markdown_directory_streaming(
        args.md_dir,
        collection,
        batch_size=args.batch_size,
        test_only=args.test_only,
        per_file_output_dir=args.output_dir,
        per_file_chunked_json_dir=args.chunked_json_dir,
    )

    if stats.get("total_chunks", 0) == 0:
        print("\n❌ No chunks created. Please check your markdown files.")
        return

    # Save metadata using aggregated stats
    embedder.save_metadata_from_stats(stats)
    
    # Verify embeddings
    embedder.verify_embeddings(collection)
    
    print("\n✅ SQL Knowledge Base embedding creation completed!")
    print(f"📊 Total documents in collection: {collection.count()}")


if __name__ == "__main__":
    main()
