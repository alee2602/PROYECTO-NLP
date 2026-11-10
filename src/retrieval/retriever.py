from src.schemas.chunk import ChunkMetadata

from .embeddings import DEFAULT_MODEL_NAME, embed_texts
from .index import ScoredChunk, VectorIndex

# Dimension of paraphrase-multilingual-MiniLM-L12-v2 (anteproyecto sección 10).
DEFAULT_EMBEDDING_DIM = 384


class SemanticRetriever:
    """Línea base de recuperación: solo búsqueda semántica (sin BM25/híbrido,
    eso llega en Fase 3 — ver TODO.md)."""

    def __init__(
        self, model_name: str = DEFAULT_MODEL_NAME, dimension: int = DEFAULT_EMBEDDING_DIM
    ):
        self.model_name = model_name
        self.index = VectorIndex(dimension=dimension)

    def index_chunks(self, chunks: list[ChunkMetadata]) -> None:
        if not chunks:
            return
        embeddings = embed_texts([c.text for c in chunks], model_name=self.model_name)
        self.index.add(chunks, embeddings)

    def search(self, query: str, top_k: int = 5) -> list[ScoredChunk]:
        query_embedding = embed_texts([query], model_name=self.model_name)[0]
        return self.index.search(query_embedding, top_k=top_k)
