"""
Shared embedding function used by both the ingestion pipeline
(document_ingestion.py) and the retriever (kb_retriever.py), so
they always encode with the exact same model wrapper ChromaDB stores
alongside a collection.
"""

from typing import List

from chromadb.utils import embedding_functions


class BGE_M3_EmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Custom embedding function for ChromaDB using BGE-M3"""

    def __init__(self, model):
        """Wrap an already-loaded SentenceTransformer model for use as a ChromaDB embedding function.

        Args:
            model: A loaded BGE-M3 SentenceTransformer instance.
        """
        self.model = model

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Encode a batch of texts into embedding vectors, as required by ChromaDB's EmbeddingFunction interface.

        Args:
            input: Texts to embed.

        Returns:
            One embedding vector per input text.
        """
        embeddings = self.model.encode(input, show_progress_bar=False)
        return embeddings.tolist()
