import json

from src.agent.evaluate_evidence import RESPONSE_SCHEMA, evaluate_claim
from src.retrieval.index import ScoredChunk
from src.schemas.chunk import ChunkMetadata
from src.schemas.output import EvidenceLevel


def test_response_schema_requires_non_empty_answer():
    """Regression test: el LLM a veces devolvía answer="" incluso al
    abstenerse (ver DECISIONS.md). El esquema ahora lo prohíbe a nivel de
    grammar, no solo por instrucción en el prompt."""
    assert RESPONSE_SCHEMA["properties"]["answer"].get("minLength") == 1


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
    contradiction_check_response = json.dumps({"stance": "respalda"})
    client = FakeClient([valid_response, contradiction_check_response])

    result = evaluate_claim("TC01", "FAISS se usa para indexar vectores.", _make_evidence(), client=client)

    assert result.evidence_level == EvidenceLevel.SUFICIENTE
    assert result.sources[0].chunk_id == "D01_0000"
    # 1 llamada a evaluate_evidence + 1 a contradiction_check (solo se activa
    # para evidencia_suficiente, ver src/agent/contradiction_check.py).
    assert client.calls == 2


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


def test_evaluate_claim_rejects_hallucinated_citation_to_absent_source():
    """SEC05 (anteproyecto sección 13): 'dame la página exacta donde Smith
    (2021) dice X', con Smith ausente del corpus -- aunque el LLM invente una
    cita con pinta de válida, validate_citations la rechaza de forma
    determinística porque el chunk_id citado no está entre los recuperados."""
    hallucinated_response = json.dumps(
        {
            "answer": "Smith (2021) afirma X en la página 7.",
            "sources": [{"source": "Smith2021", "page": 7, "chunk_id": "SMITH2021_0007"}],
            "abstained": False,
            "evidence_level": "evidencia_suficiente",
            "needs_human_review": False,
        }
    )
    client = FakeClient([hallucinated_response])

    result = evaluate_claim(
        "SEC05", "Dame la página exacta donde Smith (2021) dice X.", _make_evidence(), client=client
    )

    assert result.abstained is True
    assert result.needs_human_review is True
    assert result.sources == []
    assert result.evidence_level == EvidenceLevel.NO_LOCALIZADA
