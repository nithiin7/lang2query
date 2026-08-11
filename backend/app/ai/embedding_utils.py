"""
Shared embedding function used by both the ingestion pipeline
(document_ingestion.py) and the retriever (retrieve_sql_kb.py), so
they always encode with the exact same model wrapper ChromaDB stores
alongside a collection.
"""

from typing import List

from chromadb.utils import embedding_functions


class BGE_M3_EmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Custom embedding function for ChromaDB using BGE-M3"""

    def __init__(self, model):
        self.model = model

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(input, show_progress_bar=False)
        return embeddings.tolist()
