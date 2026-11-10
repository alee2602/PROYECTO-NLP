import json

from src.agent.evaluate_evidence import evaluate_claim
from src.retrieval.index import ScoredChunk
from src.schemas.chunk import ChunkMetadata
from src.schemas.output import EvidenceLevel


class FakeClient:
    """Stands in for LLMClient so these tests don't need LM Studio (or any
    LLM) actually running."""

    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls = 0

    def chat(self, **kwargs):
        content = self._contents[min(self.calls, len(self._contents) - 1)]
        self.calls += 1
        return {"choices": [{"message": {"content": content}}]}


def _make_evidence() -> list[ScoredChunk]:
    chunk = ChunkMetadata(
        chunk_id="D01_0000", document_id="D01", text="FAISS indexa vectores.", page=3, source="D01"
    )
    return [ScoredChunk(chunk=chunk, score=0.9)]


def test_evaluate_claim_returns_valid_output_on_first_try():
    valid_response = json.dumps(
        {
            "answer": "Evidencia suficiente: D01 (p. 3) respalda la afirmación.",
            "sources": [{"source": "D01", "page": 3, "chunk_id": "D01_0000"}],
            "abstained": False,
            "evidence_level": "evidencia_suficiente",
            "needs_human_review": False,
        }
    )
    client = FakeClient([valid_response])

    result = evaluate_claim("TC01", "FAISS se usa para indexar vectores.", _make_evidence(), client=client)

    assert result.evidence_level == EvidenceLevel.SUFICIENTE
    assert result.sources[0].chunk_id == "D01_0000"
    assert client.calls == 1


def test_evaluate_claim_retries_once_then_succeeds():
    invalid_response = "not valid json"
    valid_response = json.dumps(
        {
            "answer": "Evidencia no localizada.",
            "sources": [],
            "abstained": True,
            "evidence_level": "evidencia_no_localizada",
            "needs_human_review": True,
        }
    )
    client = FakeClient([invalid_response, valid_response])

    result = evaluate_claim("TC17", "Afirmación sin respaldo.", [], client=client)

    assert result.abstained is True
    assert client.calls == 2


def test_evaluate_claim_abstains_after_exhausting_retries():
    client = FakeClient(["not valid json", "still not valid json"])

    result = evaluate_claim("TC18", "Afirmación problemática.", _make_evidence(), client=client)

    assert result.abstained is True
    assert result.needs_human_review is True
    assert result.evidence_level == EvidenceLevel.NO_LOCALIZADA
    assert client.calls == 2
