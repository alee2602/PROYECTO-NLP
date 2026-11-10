from src.retrieval.retriever import SemanticRetriever
from src.schemas.chunk import ChunkMetadata


def _make_chunk(chunk_id: str, document_id: str, page: int, text: str) -> ChunkMetadata:
    return ChunkMetadata(
        chunk_id=chunk_id, document_id=document_id, text=text, page=page, source=document_id
    )


def test_semantic_retriever_ranks_relevant_chunk_first():
    chunks = [
        _make_chunk(
            "D01_0000",
            "D01",
            3,
            "El modelo BM25 es una función de ranking basada en frecuencia de "
            "términos y longitud del documento, usada en búsqueda léxica.",
        ),
        _make_chunk(
            "D02_0000",
            "D02",
            5,
            "La receta de pastel de chocolate lleva harina, azúcar, huevos y "
            "cacao en polvo horneado a 180 grados.",
        ),
        _make_chunk(
            "D03_0000",
            "D03",
            1,
            "FAISS es una librería para búsqueda eficiente de similitud entre "
            "vectores de alta dimensión, usada en recuperación semántica.",
        ),
    ]

    retriever = SemanticRetriever()
    retriever.index_chunks(chunks)

    results = retriever.search(
        "¿Qué librería se usa para indexar vectores y buscar por similitud?",
        top_k=2,
    )

    assert len(results) == 2
    assert results[0].chunk.chunk_id == "D03_0000"
    assert results[0].chunk.page == 1
    assert results[0].score > results[1].score
