from enum import Enum

from pydantic import BaseModel, model_validator


class EvidenceLevel(str, Enum):
    SUFICIENTE = "evidencia_suficiente"
    PARCIAL = "evidencia_parcial"
    NO_LOCALIZADA = "evidencia_no_localizada"


class SourceRef(BaseModel):
    source: str
    page: int
    chunk_id: str


class EvidentiaOutput(BaseModel):
    """Esquema de salida obligatorio del curso (answer/sources/abstained/
    tool_used/needs_human_review), con evidence_level y claim/claim_id como
    extensión propia de Evidentia (anteproyecto sección 11)."""

    answer: str
    sources: list[SourceRef] = []
    abstained: bool
    tool_used: str | None = None
    needs_human_review: bool
    claim_id: str
    claim: str
    evidence_level: EvidenceLevel

    @model_validator(mode="after")
    def check_consistency(self):
        if self.abstained:
            if self.sources:
                raise ValueError("abstained=True requires sources to be empty")
            if self.evidence_level != EvidenceLevel.NO_LOCALIZADA:
                raise ValueError(
                    "abstained=True requires evidence_level=evidencia_no_localizada"
                )
            if not self.needs_human_review:
                # Fase 5 / SEC04-SEC05 (anteproyecto sección 13): una abstención
                # debe detenerse y pedir confirmación humana, no quedar silenciosa.
                raise ValueError("abstained=True requires needs_human_review=True")
        if self.evidence_level == EvidenceLevel.SUFICIENTE and not self.sources:
            raise ValueError(
                "evidence_level=evidencia_suficiente requires at least one source"
            )
        return self
