import numpy as np
import pytest

from src.retrieval.index import VectorIndex
from src.schemas.chunk import ChunkMetadata


def _make_chunk(chunk_id: str, text: str) -> ChunkMetadata:
    return ChunkMetadata(
        chunk_id=chunk_id,
        document_id="D01",
        text=text,
        page=1,
        source="test-source",
    )


def test_add_and_search_returns_closest_vector():
    index = VectorIndex(dimension=3)
    chunks = [_make_chunk("c1", "about cats"), _make_chunk("c2", "about dogs")]
    embeddings = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype="float32"
    )
    index.add(chunks, embeddings)

    results = index.search(np.array([0.9, 0.1, 0.0], dtype="float32"), top_k=1)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "c1"


def test_search_respects_top_k_and_caps_at_index_size():
    index = VectorIndex(dimension=2)
    chunks = [_make_chunk(f"c{i}", f"text {i}") for i in range(3)]
    embeddings = np.eye(3, 2, dtype="float32")  # 3 vectors in 2D, degenerate but valid
    index.add(chunks, embeddings)

    results = index.search(np.array([1.0, 0.0], dtype="float32"), top_k=100)

    assert len(results) == len(index) == 3


def test_search_on_empty_index_returns_empty_list():
    index = VectorIndex(dimension=4)
    results = index.search(np.zeros(4, dtype="float32"), top_k=5)
    assert results == []


def test_add_rejects_mismatched_lengths():
    index = VectorIndex(dimension=2)
    chunks = [_make_chunk("c1", "x")]
    embeddings = np.zeros((2, 2), dtype="float32")
    with pytest.raises(ValueError):
        index.add(chunks, embeddings)


def test_add_rejects_wrong_dimension():
    index = VectorIndex(dimension=3)
    chunks = [_make_chunk("c1", "x")]
    embeddings = np.zeros((1, 2), dtype="float32")
    with pytest.raises(ValueError):
        index.add(chunks, embeddings)
