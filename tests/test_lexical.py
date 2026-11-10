from src.retrieval.lexical import LexicalIndex, tokenize
from src.schemas.chunk import ChunkMetadata


def _make_chunk(chunk_id: str, text: str) -> ChunkMetadata:
    return ChunkMetadata(chunk_id=chunk_id, document_id="D01", text=text, page=1, source="D01")


def test_tokenize_keeps_acronym_as_single_token():
    assert tokenize("BM25 is a ranking function") == ["bm25", "ranking", "function"]


def test_tokenize_filters_spanish_and_english_stopwords():
    tokens = tokenize("El modelo es una función que combina frecuencia y longitud.")
    assert "es" not in tokens
    assert "una" not in tokens
    assert "que" not in tokens
    assert "modelo" in tokens
    assert "frecuencia" in tokens


def test_search_finds_exact_keyword_match():
    index = LexicalIndex()
    index.add(
        [
            _make_chunk("c1", "BM25 combines term frequency and document length for ranking."),
            _make_chunk("c2", "This paper discusses image generation with diffusion models."),
            _make_chunk("c3", "FAISS is a library for approximate nearest neighbor search."),
        ]
    )

    results = index.search("How does BM25 ranking work?", top_k=1)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "c1"


def test_search_on_empty_index_returns_empty_list():
    index = LexicalIndex()
    assert index.search("anything", top_k=5) == []


def test_search_respects_top_k():
    index = LexicalIndex()
    index.add([_make_chunk(f"c{i}", f"document number {i} about retrieval") for i in range(5)])

    results = index.search("retrieval document", top_k=2)

    assert len(results) == 2
