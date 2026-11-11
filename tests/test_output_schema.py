import pytest
from pydantic import ValidationError

from src.schemas.output import EvidenceLevel, EvidentiaOutput, SourceRef


def _base_kwargs(**overrides):
    kwargs = dict(
        answer="Evidencia suficiente: D01 (p. 3) respalda la afirmación.",
        sources=[SourceRef(source="D01", page=3, chunk_id="D01_0000")],
        abstained=False,
        tool_used="search_evidence",
        needs_human_review=False,
        claim_id="TC01",
        claim="Alguna afirmación.",
        evidence_level=EvidenceLevel.SUFICIENTE,
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_suficiente_output_is_accepted():
    output = EvidentiaOutput(**_base_kwargs())
    assert output.evidence_level == EvidenceLevel.SUFICIENTE
    assert len(output.sources) == 1


def test_valid_abstention_output_is_accepted():
    output = EvidentiaOutput(
        **_base_kwargs(
            sources=[],
            abstained=True,
            tool_used=None,
            needs_human_review=True,
            evidence_level=EvidenceLevel.NO_LOCALIZADA,
        )
    )
    assert output.abstained is True
    assert output.sources == []


def test_abstained_with_sources_is_rejected():
    with pytest.raises(ValidationError):
        EvidentiaOutput(
            **_base_kwargs(abstained=True, evidence_level=EvidenceLevel.NO_LOCALIZADA)
        )


def test_abstained_with_wrong_evidence_level_is_rejected():
    with pytest.raises(ValidationError):
        EvidentiaOutput(
            **_base_kwargs(sources=[], abstained=True, evidence_level=EvidenceLevel.PARCIAL)
        )


def test_suficiente_without_sources_is_rejected():
    with pytest.raises(ValidationError):
        EvidentiaOutput(**_base_kwargs(sources=[], evidence_level=EvidenceLevel.SUFICIENTE))


def test_abstained_without_human_review_is_rejected():
    """Fase 5 (SEC04/SEC05, anteproyecto sección 13): una abstención debe
    detenerse y pedir confirmación humana, nunca quedar silenciosa."""
    with pytest.raises(ValidationError):
        EvidentiaOutput(
            **_base_kwargs(
                sources=[],
                abstained=True,
                needs_human_review=False,
                evidence_level=EvidenceLevel.NO_LOCALIZADA,
            )
        )
