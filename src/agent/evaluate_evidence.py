import json

import requests
from pydantic import ValidationError

from src.retrieval.index import ScoredChunk
from src.schemas.output import EvidenceLevel, EvidentiaOutput

from .llm_client import LLMClient, generate_json, get_client

SYSTEM_PROMPT = """Eres el componente evaluate_evidence de Evidentia, un sistema \
que verifica si afirmaciones de documentos académicos tienen respaldo documental.

Reglas estrictas:
- Usa EXCLUSIVAMENTE el texto de los fragmentos de evidencia que se te dan. \
Nunca inventes fuentes, páginas ni contenido que no esté en los fragmentos.
- Si ningún fragmento respalda la afirmación, evidence_level debe ser \
"evidencia_no_localizada", abstained debe ser true, y sources debe quedar vacío.
- Si algún fragmento respalda la afirmación pero no completamente, \
evidence_level debe ser "evidencia_parcial" y needs_human_review debe ser true.
- Si uno o más fragmentos respaldan la afirmación completamente, evidence_level \
debe ser "evidencia_suficiente" y sources debe citar al menos un chunk_id de los \
fragmentos recibidos.
- Responde ÚNICAMENTE un objeto JSON con las claves: answer, sources (lista de \
objetos con source, page, chunk_id), abstained, evidence_level, needs_human_review."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "page": {"type": "integer"},
                    "chunk_id": {"type": "string"},
                },
                "required": ["source", "page", "chunk_id"],
            },
        },
        "abstained": {"type": "boolean"},
        "evidence_level": {
            "type": "string",
            "enum": [level.value for level in EvidenceLevel],
        },
        "needs_human_review": {"type": "boolean"},
    },
    "required": ["answer", "sources", "abstained", "evidence_level", "needs_human_review"],
}


def _build_user_prompt(claim: str, evidence: list[ScoredChunk]) -> str:
    fragments = "\n\n".join(
        f"[chunk_id={sc.chunk.chunk_id} source={sc.chunk.source} page={sc.chunk.page}]\n{sc.chunk.text}"
        for sc in evidence
    )
    return (
        f"Afirmación a evaluar:\n{claim}\n\n"
        f"Fragmentos de evidencia recuperados (top-{len(evidence)}):\n"
        f"{fragments or '(sin fragmentos recuperados)'}"
    )


def _abstain(claim_id: str, claim: str) -> EvidentiaOutput:
    return EvidentiaOutput(
        answer="No fue posible generar una evaluación válida para esta afirmación.",
        sources=[],
        abstained=True,
        tool_used=None,
        needs_human_review=True,
        claim_id=claim_id,
        claim=claim,
        evidence_level=EvidenceLevel.NO_LOCALIZADA,
    )


def evaluate_claim(
    claim_id: str,
    claim: str,
    evidence: list[ScoredChunk],
    client: LLMClient | None = None,
    tool_used: str = "search_evidence",
) -> EvidentiaOutput:
    """evaluate_evidence tool (anteproyecto sección 11): clasifica una
    afirmación contra la evidencia recuperada. Permite un reintento si la
    salida no valida contra el esquema o si falla la llamada al servidor;
    si vuelve a fallar, se abstiene y marca needs_human_review=True (regla
    de la sección 11)."""
    client = client or get_client()
    user_prompt = _build_user_prompt(claim, evidence)

    for _ in range(2):
        try:
            raw = generate_json(
                client, SYSTEM_PROMPT, user_prompt, RESPONSE_SCHEMA, schema_name="evaluate_evidence"
            )
            raw["claim_id"] = claim_id
            raw["claim"] = claim
            raw["tool_used"] = tool_used if evidence else None
            return EvidentiaOutput(**raw)
        except (ValidationError, json.JSONDecodeError, KeyError, TypeError, requests.RequestException):
            continue

    return _abstain(claim_id, claim)
