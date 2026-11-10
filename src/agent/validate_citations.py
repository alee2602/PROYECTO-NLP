import re

from src.retrieval.index import ScoredChunk
from src.schemas.output import EvidenceLevel, EvidentiaOutput

# Captura cifras y porcentajes ("45%", "10,000", "3.5") para el chequeo de
# fundamentación numérica.
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?%?")

# Los identificadores arXiv ("arXiv:2502.13141", opcionalmente con "v2") son
# una ETIQUETA para referirse al paper, no un dato factual a verificar — el
# chunker a menudo separa el header/abstract (donde está el ID) del cuerpo
# del texto que respalda la afirmación real, así que exigir que el número
# del ID aparezca en el chunk citado genera falsos negativos (ver
# DECISIONS.md: afectaba 4 de 7 casos de clasificación incorrecta).
_ARXIV_ID_RE = re.compile(r"arxiv:\s*\d{4}\.\d{4,5}(?:v\d+)?", re.IGNORECASE)


def _extract_numbers(text: str) -> set[str]:
    text_without_arxiv_ids = _ARXIV_ID_RE.sub("", text)
    return set(_NUMBER_RE.findall(text_without_arxiv_ids))


def _with_updates(output: EvidentiaOutput, **updates) -> EvidentiaOutput:
    """Reconstruye el objeto pasando por el constructor (no model_copy) para
    que las reglas de consistencia de EvidentiaOutput se vuelvan a validar."""
    data = output.model_dump()
    data.update(updates)
    return EvidentiaOutput(**data)


def validate_citations(output: EvidentiaOutput, evidence: list[ScoredChunk]) -> EvidentiaOutput:
    """validate_citations tool (anteproyecto sección 11): verificación
    determinística y posterior al LLM — no se le pide al modelo que "tenga
    cuidado", se comprueba con código si lo que dijo es cierto. Ver
    DECISIONS.md: el LLM (7B local) validaba cifras inventadas como
    "evidencia_suficiente" pese a instrucciones explícitas en el prompt."""
    if not output.sources:
        return output

    evidence_by_id = {sc.chunk.chunk_id: sc.chunk for sc in evidence}

    # 1) Toda cita debe corresponder a un chunk realmente recuperado, no
    # inventado por el modelo.
    for source in output.sources:
        if source.chunk_id not in evidence_by_id:
            return _with_updates(
                output,
                evidence_level=EvidenceLevel.NO_LOCALIZADA,
                abstained=True,
                sources=[],
                needs_human_review=True,
                answer=f"{output.answer} [validate_citations: cita a un chunk no recuperado; descartada]",
            )

    # 2) Si la afirmación incluye una cifra específica, debe aparecer
    # literalmente en el texto de al menos uno de los chunks citados para
    # sostener "evidencia_suficiente".
    claim_numbers = _extract_numbers(output.claim)
    if claim_numbers and output.evidence_level == EvidenceLevel.SUFICIENTE:
        cited_text = " ".join(evidence_by_id[s.chunk_id].text for s in output.sources)
        cited_numbers = _extract_numbers(cited_text)
        if not claim_numbers & cited_numbers:
            return _with_updates(
                output,
                evidence_level=EvidenceLevel.PARCIAL,
                needs_human_review=True,
                answer=(
                    f"{output.answer} [validate_citations: la(s) cifra(s) de la afirmación "
                    "no aparecen literalmente en la fuente citada; requiere revisión manual]"
                ),
            )

    return output
