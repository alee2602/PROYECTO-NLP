import json

from src.agent.orchestrator import DEFAULT_TOP_K, REFINED_TOP_K, run_pipeline
from src.retrieval.index import ScoredChunk
from src.schemas.chunk import ChunkMetadata
from src.schemas.output import EvidenceLevel


class FakeClient:
    """Devuelve las respuestas en orden: primero la de extract_claims, luego
    una por cada llamada a evaluate_claim (en el orden en que ocurren)."""

    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls = 0

    def chat(self, **kwargs):
        content = self._contents[min(self.calls, len(self._contents) - 1)]
        self.calls += 1
        return {"choices": [{"message": {"content": content}}]}


class FakeRetriever:
    def __init__(self):
        self.calls: list[tuple[str, int]] = []
        chunk = ChunkMetadata(
            chunk_id="D01_0000", document_id="D01", text="texto de evidencia", page=1, source="D01"
        )
        self._evidence = [ScoredChunk(chunk=chunk, score=0.9)]

    def search(self, query: str, top_k: int = 5):
        self.calls.append((query, top_k))
        return self._evidence


def _suficiente_response(claim_num: int = 0) -> str:
    return json.dumps(
        {
            "answer": f"Respaldo encontrado para la afirmación {claim_num}.",
            "sources": [{"source": "D01", "page": 1, "chunk_id": "D01_0000"}],
            "abstained": False,
            "evidence_level": "evidencia_suficiente",
            "needs_human_review": False,
        }
    )


def _no_localizada_response() -> str:
    return json.dumps(
        {
            "answer": "No se encontró evidencia.",
            "sources": [],
            "abstained": True,
            "evidence_level": "evidencia_no_localizada",
            "needs_human_review": False,
        }
    )


def test_pipeline_processes_all_extracted_claims():
    extract_response = json.dumps(
        {"claims": [{"text": "Afirmación uno."}, {"text": "Afirmación dos."}]}
    )
    client = FakeClient([extract_response, _suficiente_response(1), _suficiente_response(2)])
    retriever = FakeRetriever()

    results = run_pipeline("documento de prueba", retriever=retriever, client=client)

    assert len(results) == 2
    assert all(r.evidence_level == EvidenceLevel.SUFICIENTE for r in results)
    assert client.calls == 3  # 1 extract + 2 evaluate
    assert len(retriever.calls) == 2


def test_pipeline_returns_empty_results_when_no_claims_extracted():
    client = FakeClient([json.dumps({"claims": []})])
    retriever = FakeRetriever()

    results = run_pipeline("documento sin afirmaciones", retriever=retriever, client=client)

    assert results == []
    assert retriever.calls == []


def test_pipeline_refines_search_once_when_no_evidence_found():
    extract_response = json.dumps({"claims": [{"text": "Afirmación difícil de verificar."}]})
    client = FakeClient(
        [extract_response, _no_localizada_response(), _suficiente_response(1)]
    )
    retriever = FakeRetriever()

    results = run_pipeline("documento", retriever=retriever, client=client)

    assert len(results) == 1
    assert results[0].evidence_level == EvidenceLevel.SUFICIENTE  # el segundo intento sí encontró
    assert retriever.calls == [
        ("Afirmación difícil de verificar.", DEFAULT_TOP_K),
        ("Afirmación difícil de verificar.", REFINED_TOP_K),
    ]
    assert client.calls == 3  # 1 extract + 2 evaluate (original + refinado)


def test_pipeline_does_not_refine_more_than_once():
    extract_response = json.dumps({"claims": [{"text": "Afirmación sin respaldo en el corpus."}]})
    client = FakeClient([extract_response, _no_localizada_response(), _no_localizada_response()])
    retriever = FakeRetriever()

    results = run_pipeline("documento", retriever=retriever, client=client)

    assert len(results) == 1
    assert results[0].evidence_level == EvidenceLevel.NO_LOCALIZADA
    assert len(retriever.calls) == 2  # original + un solo refinamiento, no más
