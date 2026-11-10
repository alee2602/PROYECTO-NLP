import json

from src.agent.contradiction_check import check_contradiction, check_stance
from src.retrieval.index import ScoredChunk
from src.schemas.chunk import ChunkMetadata
from src.schemas.output import EvidenceLevel, EvidentiaOutput, SourceRef


class FakeClient:
    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls = 0

    def chat(self, **kwargs):
        content = self._contents[min(self.calls, len(self._contents) - 1)]
        self.calls += 1
        return {"choices": [{"message": {"content": content}}]}


def _make_evidence(chunk_id: str = "D01_0000", text: str = "texto") -> list[ScoredChunk]:
    chunk = ChunkMetadata(chunk_id=chunk_id, document_id="D01", text=text, page=1, source="D01")
    return [ScoredChunk(chunk=chunk, score=0.9)]


def _suficiente_output(claim: str, chunk_id: str = "D01_0000") -> EvidentiaOutput:
    return EvidentiaOutput(
        answer="El fragmento respalda la afirmación.",
        sources=[SourceRef(source="D01", page=1, chunk_id=chunk_id)],
        abstained=False,
        tool_used="search_evidence",
        needs_human_review=False,
        claim_id="TC01",
        claim=claim,
        evidence_level=EvidenceLevel.SUFICIENTE,
    )


def test_check_stance_parses_valid_response():
    client = FakeClient([json.dumps({"stance": "contradice"})])
    assert check_stance("alguna afirmación", "algún fragmento", client=client) == "contradice"


def test_check_stance_defaults_to_irrelevante_on_malformed_response():
    client = FakeClient(["not valid json"])
    assert check_stance("alguna afirmación", "algún fragmento", client=client) == "irrelevante"


def test_check_contradiction_downgrades_when_cited_chunk_contradicts():
    output = _suficiente_output("Los sistemas automatizados no reducen el tiempo requerido.")
    evidence = _make_evidence(text="Los sistemas automatizados sí reducen el tiempo requerido.")
    client = FakeClient([json.dumps({"stance": "contradice"})])

    result = check_contradiction(output, evidence, client=client)

    assert result.evidence_level == EvidenceLevel.PARCIAL
    assert result.needs_human_review is True
    assert "contradiction_check" in result.answer


def test_check_contradiction_keeps_suficiente_when_chunk_supports():
    output = _suficiente_output("El modelo produce vectores de 768 dimensiones.")
    evidence = _make_evidence(text="El modelo produce vectores de 768 dimensiones.")
    client = FakeClient([json.dumps({"stance": "respalda"})])

    result = check_contradiction(output, evidence, client=client)

    assert result.evidence_level == EvidenceLevel.SUFICIENTE
    assert result.needs_human_review is False


def test_check_contradiction_skips_non_suficiente_outputs():
    output = _suficiente_output("afirmación cualquiera")
    output = output.model_copy(update={"evidence_level": EvidenceLevel.PARCIAL})
    client = FakeClient([json.dumps({"stance": "contradice"})])

    result = check_contradiction(output, _make_evidence(), client=client)

    assert result is output
    assert client.calls == 0


def test_check_contradiction_skips_outputs_without_sources():
    output = _suficiente_output("afirmación cualquiera").model_copy(update={"sources": []})
    client = FakeClient([json.dumps({"stance": "contradice"})])

    result = check_contradiction(output, _make_evidence(), client=client)

    assert result is output
    assert client.calls == 0
