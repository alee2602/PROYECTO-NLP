from src.retrieval.hybrid import HybridRetriever
from src.schemas.chunk import ChunkMetadata


def _make_chunk(chunk_id: str, document_id: str, text: str) -> ChunkMetadata:
    return ChunkMetadata(
        chunk_id=chunk_id, document_id=document_id, text=text, page=1, source=document_id
    )


def test_hybrid_finds_exact_term_chunk_missed_by_semantic_alone():
    """Regression test for the bug found in scripts/demo.py (ver DECISIONS.md):
    una pregunta sobre un término técnico exacto (BM25) no encontraba el chunk
    que literalmente lo menciona cuando solo se usaba búsqueda semántica."""
    chunks = [
        _make_chunk(
            "D04_0000",
            "D04",
            "IITP@COLIEE 2019: Legal Information Retrieval using BM25 and BERT "
            "for ranking legal case documents.",
        ),
        _make_chunk(
            "D01_0000",
            "D01",
            "Autoregressive retrieval augmentation improves image generation "
            "quality on dense prompt benchmarks.",
        ),
        _make_chunk(
            "D03_0000",
            "D03",
            "A beam search decoding algorithm selects the most probable "
            "document identifier during generative retrieval.",
        ),
    ]

    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    results = retriever.search(
        "BM25 es una función de ranking que combina frecuencia de términos y "
        "longitud del documento para recuperación léxica.",
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "D04_0000"


def test_hybrid_search_on_empty_index_returns_empty_list():
    retriever = HybridRetriever()
    assert retriever.search("anything", top_k=5) == []


def test_hybrid_respects_top_k():
    chunks = [_make_chunk(f"c{i}", "D01", f"retrieval topic number {i}") for i in range(10)]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    results = retriever.search("retrieval topic", top_k=3)

    assert len(results) == 3


def test_hybrid_enforces_hard_top_k_cap():
    from src.limits import MAX_TOP_K

    chunks = [_make_chunk(f"c{i}", "D01", f"retrieval topic number {i}") for i in range(40)]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    results = retriever.search("retrieval topic", top_k=500)

    assert len(results) == MAX_TOP_K


def test_hybrid_top_k_below_one_returns_at_least_one():
    chunks = [_make_chunk(f"c{i}", "D01", f"retrieval topic number {i}") for i in range(3)]
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    assert len(retriever.search("retrieval topic", top_k=0)) == 1
