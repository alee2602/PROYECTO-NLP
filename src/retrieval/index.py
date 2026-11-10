from dataclasses import dataclass, field

import faiss
import numpy as np

from src.schemas.chunk import ChunkMetadata


@dataclass
class ScoredChunk:
    chunk: ChunkMetadata
    score: float


class VectorIndex:
    """Wraps a FAISS IndexFlatIP (exact search, cosine similarity on
    normalized vectors) and keeps the chunk metadata aligned with each
    vector's position (anteproyecto sección 10: FAISS como índice inicial)."""

    def __init__(self, dimension: int):
        self.dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)
        self._chunks: list[ChunkMetadata] = []

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: list[ChunkMetadata], embeddings: np.ndarray) -> None:
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({embeddings.shape[0]}) "
                "must have the same length"
            )
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"embedding dimension {embeddings.shape[1]} != index dimension {self.dimension}"
            )
        self._index.add(np.ascontiguousarray(embeddings, dtype="float32"))
        self._chunks.extend(chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[ScoredChunk]:
        if len(self._chunks) == 0:
            return []
        top_k = min(top_k, len(self._chunks))
        query = np.ascontiguousarray(query_embedding, dtype="float32").reshape(1, -1)
        scores, ids = self._index.search(query, top_k)
        return [
            ScoredChunk(chunk=self._chunks[idx], score=float(score))
            for score, idx in zip(scores[0], ids[0])
            if idx != -1
        ]
