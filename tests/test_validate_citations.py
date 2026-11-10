from src.agent.validate_citations import validate_citations
from src.retrieval.index import ScoredChunk
from src.schemas.chunk import ChunkMetadata
from src.schemas.output import EvidenceLevel, EvidentiaOutput, SourceRef


def _make_evidence(chunk_id: str, text: str) -> list[ScoredChunk]:
    chunk = ChunkMetadata(chunk_id=chunk_id, document_id="D01", text=text, page=2, source="D01")
    return [ScoredChunk(chunk=chunk, score=0.9)]


def _base_output(**overrides) -> EvidentiaOutput:
    kwargs = dict(
        answer="El fragmento respalda la afirmación.",
        sources=[SourceRef(source="D01", page=2, chunk_id="D01_0000")],
        abstained=False,
        tool_used="search_evidence",
        needs_human_review=False,
        claim_id="TC01",
        claim="El modelo produce vectores de 768 dimensiones.",
        evidence_level=EvidenceLevel.SUFICIENTE,
    )
    kwargs.update(overrides)
    return EvidentiaOutput(**kwargs)


def test_passes_through_when_no_sources():
    output = _base_output(sources=[], abstained=True, evidence_level=EvidenceLevel.NO_LOCALIZADA)
    result = validate_citations(output, evidence=[])
    assert result == output


def test_rejects_citation_to_chunk_not_in_evidence():
    output = _base_output()
    evidence = _make_evidence("D01_9999", "contenido no relacionado")

    result = validate_citations(output, evidence)

    assert result.abstained is True
    assert result.sources == []
    assert result.evidence_level == EvidenceLevel.NO_LOCALIZADA
    assert result.needs_human_review is True


def test_downgrades_suficiente_when_claim_number_missing_from_cited_text():
    output = _base_output(claim="El sistema mejora el rendimiento en un 45%.")
    evidence = _make_evidence("D01_0000", "El sistema mejora el rendimiento de forma notable.")

    result = validate_citations(output, evidence)

    assert result.evidence_level == EvidenceLevel.PARCIAL
    assert result.needs_human_review is True
    assert "45" not in "".join(sc.chunk.text for sc in evidence)


def test_keeps_suficiente_when_claim_number_is_in_cited_text():
    output = _base_output(claim="El modelo produce vectores de 768 dimensiones.")
    evidence = _make_evidence("D01_0000", "El modelo produce vectores de 768 dimensiones.")

    result = validate_citations(output, evidence)

    assert result.evidence_level == EvidenceLevel.SUFICIENTE
    assert result.needs_human_review is False


def test_does_not_touch_non_suficiente_outputs_even_with_missing_numbers():
    output = _base_output(
        claim="El sistema mejora el rendimiento en un 45%.",
        evidence_level=EvidenceLevel.PARCIAL,
        needs_human_review=True,
    )
    evidence = _make_evidence("D01_0000", "El sistema mejora el rendimiento de forma notable.")

    result = validate_citations(output, evidence)

    assert result.evidence_level == EvidenceLevel.PARCIAL
