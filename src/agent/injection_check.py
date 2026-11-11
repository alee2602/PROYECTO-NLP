from src.retrieval.index import ScoredChunk
from src.schemas.output import EvidenceLevel, EvidentiaOutput
from src.security.injection_guard import detect_injection


def check_injection(output: EvidentiaOutput, evidence: list[ScoredChunk]) -> EvidentiaOutput:
    """check_injection tool (anteproyecto sección 13, SEC01/SEC02):
    verificación determinística y posterior al LLM, igual que
    validate_citations -- no se le pide al modelo que "detecte" un intento
    de manipulación, se busca el patrón con código. Si la afirmación del
    usuario o algún fragmento de evidencia recuperado contiene un patrón de
    inyección de instrucciones, no se confía en que el modelo lo haya
    ignorado solo porque el prompt se lo pide: se degrada a revisión humana."""
    suspicious = detect_injection(output.claim) or any(
        detect_injection(sc.chunk.text) for sc in evidence
    )
    if not suspicious:
        return output

    data = output.model_dump()
    data["needs_human_review"] = True
    if output.evidence_level == EvidenceLevel.SUFICIENTE:
        data["evidence_level"] = EvidenceLevel.PARCIAL
    data["answer"] = (
        f"{output.answer} [security: se detectó un patrón de posible inyección de "
        "instrucciones en la afirmación o en la evidencia; requiere revisión manual]"
    )
    return EvidentiaOutput(**data)
