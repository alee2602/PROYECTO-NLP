import json

import requests
from pydantic import ValidationError

from src.retrieval.index import ScoredChunk
from src.schemas.output import EvidenceLevel, EvidentiaOutput

from .contradiction_check import check_contradiction
from .llm_client import LLMClient, generate_json, get_client
from .validate_citations import validate_citations

SYSTEM_PROMPT = """Eres el componente evaluate_evidence de Evidentia, un sistema \
que verifica si afirmaciones de documentos académicos tienen respaldo documental.

Antes de responder, identifica mentalmente qué dice cada fragmento en relación \
a la afirmación (¿la respalda, la contradice, la respalda solo en parte, o no \
dice nada relevante?) y usa eso para decidir evidence_level. Nunca clasifiques \
solo por similitud superficial de palabras.

Reglas estrictas:
- Usa EXCLUSIVAMENTE el texto de los fragmentos de evidencia que se te dan. \
Nunca inventes fuentes, páginas ni contenido que no esté en los fragmentos.
- Si uno o más fragmentos respaldan la afirmación completamente y sin \
contradicción, evidence_level="evidencia_suficiente", sources debe citar al \
menos un chunk_id de los fragmentos recibidos, abstained=false.
- Si algún fragmento respalda la afirmación solo parcialmente (le falta un \
dato, cubre solo una parte de una afirmación compuesta, o es ambiguo), \
evidence_level="evidencia_parcial", needs_human_review=true.
- Si uno o más fragmentos CONTRADICEN o REFUTAN la afirmación (muestran que es \
falsa, exagerada, o que existe una excepción documentada), evidence_level= \
"evidencia_parcial" — NUNCA "evidencia_suficiente" — y needs_human_review=true. \
"evidencia_suficiente" significa que la evidencia RESPALDA la afirmación tal \
como está escrita, no que la evidencia permita saber que es falsa.
- Si ningún fragmento es relevante para la afirmación, evidence_level= \
"evidencia_no_localizada", abstained=true, y sources debe quedar vacío.
- El campo answer NUNCA debe quedar vacío y debe justificar la clasificación \
citando lo que dice el fragmento relevante (no solo repetir la afirmación).

Ejemplos (afirmación → fragmento relevante → clasificación correcta):
1. "El modelo X usa 768 dimensiones" → fragmento dice "el modelo X produce \
vectores de 768 dimensiones" → evidencia_suficiente, sources=[ese chunk], \
answer explica que el fragmento confirma la cifra.
2. "La técnica X es imposible de detectar" → fragmento describe un método que \
SÍ detecta X → evidencia_parcial (NO suficiente), needs_human_review=true, \
answer="La evidencia contradice la afirmación: el fragmento describe un \
método que detecta X.", sources=[ese chunk].
3. "El sistema Y mejora precisión y reduce costo a la mitad" → fragmento solo \
confirma la mejora de precisión, no menciona costo → evidencia_parcial, \
needs_human_review=true, answer explica qué parte sí y qué parte no está \
respaldada.
4. "El dataset Z tiene 10,000 ejemplos anotados a mano" → ningún fragmento \
menciona el tamaño del dataset ni cómo fue anotado → evidencia_no_localizada, \
abstained=true, sources=[], answer explica que no se encontró esa información.

- Responde ÚNICAMENTE un objeto JSON con las claves: answer, sources (lista de \
objetos con source, page, chunk_id), abstained, evidence_level, needs_human_review."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "minLength": 1},
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
            result = EvidentiaOutput(**raw)
            result = validate_citations(result, evidence)
            return check_contradiction(result, evidence, client=client)
        except (ValidationError, json.JSONDecodeError, KeyError, TypeError, requests.RequestException):
            continue

    return _abstain(claim_id, claim)
