import re

from src.schemas.chunk import ChunkMetadata

from .index import ScoredChunk
from .lexical import LexicalIndex
from .retriever import DEFAULT_EMBEDDING_DIM, SemanticRetriever

# Anteproyecto sección 10: "ponderación de 70% para búsqueda semántica y 30%
# para búsqueda léxica".
DEFAULT_SEMANTIC_WEIGHT = 0.7
DEFAULT_LEXICAL_WEIGHT = 0.3

# Las afirmaciones están en español, el corpus (arXiv) en inglés. BM25 por sí
# solo falla: palabras genéricas que existen igual en ambos idiomas (ej.
# "ranking") acumulan más coincidencias que el único token que de verdad
# importa (ej. "bm25"), diluyendo la señal (ver DECISIONS.md). Como refuerzo,
# se detectan identificadores técnicos en su forma original (BM25, RAGAS,
# FAISS, GPT4...) y se da un boost fuerte a cualquier chunk que los contenga
# literalmente, sin importar qué tan bien o mal haya rankeado por lo demás.
_IDENTIFIER_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*\d[A-Za-z0-9]*\b|\b[A-Z]{2,}\b")
IDENTIFIER_BOOST = 1.0


def _extract_identifiers(text: str) -> set[str]:
    return {match.group(0).lower() for match in _IDENTIFIER_RE.finditer(text)}


def _normalize(scores: list[float]) -> dict[int, float]:
    """Min-max normaliza una lista de scores a [0, 1] por posición, para
    poder combinar semántico (coseno) y léxico (BM25, escala distinta)."""
    if not scores:
        return {}
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return {i: 1.0 for i in range(len(scores))}
    return {i: (s - lo) / (hi - lo) for i, s in enumerate(scores)}


class HybridRetriever:
    """Recuperación híbrida semántica + léxica (Fase 3 — mejora sobre
    SemanticRetriever, la línea base de Fase 2). Ver DECISIONS.md: la
    búsqueda solo-semántica no encontraba documentos con coincidencias
    léxicas exactas obvias (ej. "BM25", "RAGAS")."""

    def __init__(
        self,
        semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
    ):
        self.semantic_weight = semantic_weight
        self.lexical_weight = lexical_weight
        self.semantic = SemanticRetriever(dimension=embedding_dim)
        self.lexical = LexicalIndex()
        self._chunks: list[ChunkMetadata] = []

    def index_chunks(self, chunks: list[ChunkMetadata]) -> None:
        if not chunks:
            return
        self.semantic.index_chunks(chunks)
        self.lexical.add(chunks)
        self._chunks.extend(chunks)

    def search(
        self, query: str, top_k: int = 5, candidate_pool: int = 20
    ) -> list[ScoredChunk]:
        n_chunks = len(self.lexical)
        if n_chunks == 0:
            return []
        pool = min(candidate_pool, n_chunks)

        semantic_hits = self.semantic.search(query, top_k=pool)
        lexical_hits = self.lexical.search(query, top_k=pool)

        semantic_norm = _normalize([hit.score for hit in semantic_hits])
        lexical_norm = _normalize([hit.score for hit in lexical_hits])

        combined: dict[str, float] = {}
        chunk_by_id: dict[str, ChunkMetadata] = {}
        for i, hit in enumerate(semantic_hits):
            chunk_by_id[hit.chunk.chunk_id] = hit.chunk
            combined[hit.chunk.chunk_id] = (
                combined.get(hit.chunk.chunk_id, 0.0) + self.semantic_weight * semantic_norm[i]
            )
        for i, hit in enumerate(lexical_hits):
            chunk_by_id[hit.chunk.chunk_id] = hit.chunk
            combined[hit.chunk.chunk_id] = (
                combined.get(hit.chunk.chunk_id, 0.0) + self.lexical_weight * lexical_norm[i]
            )

        identifiers = _extract_identifiers(query)
        if identifiers:
            for chunk in self._chunks:
                text_lower = chunk.text.lower()
                if any(identifier in text_lower for identifier in identifiers):
                    chunk_by_id[chunk.chunk_id] = chunk
                    combined[chunk.chunk_id] = combined.get(chunk.chunk_id, 0.0) + IDENTIFIER_BOOST

        ranked = sorted(combined.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [ScoredChunk(chunk=chunk_by_id[chunk_id], score=score) for chunk_id, score in ranked]
