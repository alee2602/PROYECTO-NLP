import math
import re

from src.schemas.chunk import ChunkMetadata

from .index import ScoredChunk

# Keeps alphanumeric runs together (so "BM25" stays as one token instead of
# splitting into "bm" and "25") — important for exact technical-term matches
# that semantic embeddings alone tend to underweight (ver DECISIONS.md).
_TOKEN_RE = re.compile(r"[a-záéíóúñü0-9]+")

# Defaults de BM25 estándar (Robertson & Zaragoza, 2009 — citado en el
# anteproyecto sección 16).
K1 = 1.5
B = 0.75

# Las afirmaciones del banco de pruebas están en español, pero el corpus (arXiv)
# está en inglés. Sin filtrar stopwords, palabras funcionales en español como
# "es"/"una"/"de"/"que" no matchean contra el corpus en inglés de forma real,
# pero sí generan coincidencias falsas por ruido/casualidad que distorsionan
# el ranking (ver DECISIONS.md: bug encontrado con la consulta sobre BM25).
_STOPWORDS = {
    # Español
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "a", "en", "y", "o", "que", "es", "son", "para", "por", "con", "su", "sus",
    "se", "lo", "le", "les", "como", "más", "mas", "este", "esta", "estos",
    "estas", "ese", "esa", "esos", "esas", "no", "sí", "si", "pero", "sobre",
    "entre", "sin", "hay", "ser", "está", "están", "fue", "fueron", "ha", "han",
    # English
    "the", "a", "an", "of", "in", "on", "and", "or", "to", "for", "is", "are",
    "that", "this", "these", "those", "with", "as", "by", "it", "its", "be",
    "was", "were", "has", "have", "not", "but", "from", "at",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class _BM25:
    """Implementación propia de BM25 (Okapi), sin dependencias externas —
    se evitó `rank-bm25` por ser trivial de reimplementar y no depender de
    poder instalar un paquete nuevo en cualquier máquina/red."""

    def __init__(self, corpus_tokens: list[list[str]], k1: float = K1, b: float = B):
        self.k1 = k1
        self.b = b
        self.doc_lengths = [len(doc) for doc in corpus_tokens]
        self.avgdl = sum(self.doc_lengths) / len(corpus_tokens) if corpus_tokens else 0.0

        self.doc_term_freqs: list[dict[str, int]] = []
        doc_freq: dict[str, int] = {}
        for doc in corpus_tokens:
            freqs: dict[str, int] = {}
            for term in doc:
                freqs[term] = freqs.get(term, 0) + 1
            self.doc_term_freqs.append(freqs)
            for term in freqs:
                doc_freq[term] = doc_freq.get(term, 0) + 1

        n_docs = len(corpus_tokens)
        self.idf = {
            term: math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1)
            for term, freq in doc_freq.items()
        }

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0] * len(self.doc_term_freqs)
        for i, freqs in enumerate(self.doc_term_freqs):
            doc_len = self.doc_lengths[i]
            norm = self.k1 * (1 - self.b + self.b * doc_len / self.avgdl) if self.avgdl else self.k1
            score = 0.0
            for term in query_tokens:
                f = freqs.get(term)
                if not f:
                    continue
                idf = self.idf.get(term, 0.0)
                score += idf * (f * (self.k1 + 1)) / (f + norm)
            scores[i] = score
        return scores


class LexicalIndex:
    """Búsqueda léxica BM25 (anteproyecto sección 10), complemento de
    SemanticRetriever para la estrategia híbrida."""

    def __init__(self):
        self._chunks: list[ChunkMetadata] = []
        self._bm25: _BM25 | None = None

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: list[ChunkMetadata]) -> None:
        self._chunks.extend(chunks)
        corpus_tokens = [tokenize(c.text) for c in self._chunks]
        self._bm25 = _BM25(corpus_tokens) if corpus_tokens else None

    def search(self, query: str, top_k: int = 5) -> list[ScoredChunk]:
        if not self._chunks or self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        top_k = min(top_k, len(self._chunks))
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [ScoredChunk(chunk=self._chunks[i], score=float(scores[i])) for i in top_indices]
