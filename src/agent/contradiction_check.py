import json

import requests
from pydantic import ValidationError

from src.retrieval.index import ScoredChunk
from src.schemas.output import EvidenceLevel, EvidentiaOutput

from .llm_client import LLMClient, generate_json, get_client

# Verificación separada y deliberadamente angosta: una pregunta por fragmento
# ("¿contradice, respalda, o es irrelevante?"), no el juicio holístico
# completo que ya le pedimos al LLM en evaluate_evidence. Ver DECISIONS.md:
# pedirle al modelo que evalúe contradicción DENTRO de la misma llamada que
# decide evidence_level no generalizó (TC08 volvió a fallar con una
# afirmación nueva). Una pregunta más simple, aplicada después, es más
# confiable — mismo patrón que validate_citations.
SYSTEM_PROMPT = """Te doy una afirmación y UN fragmento de un documento. Tu \
única tarea es decidir si el fragmento CONTRADICE la afirmación.

- "respalda": el fragmento confirma la afirmación o dice esencialmente lo \
mismo, aunque sea con otras palabras o de forma parcial. Si la afirmación es \
casi una repetición o resumen del fragmento, es "respalda", NO "contradice".
- "contradice": el fragmento afirma lo OPUESTO de lo que dice la afirmación \
(ej. la afirmación dice "X no ocurre" y el fragmento dice "X sí ocurre", o \
viceversa). Marca "contradice" SOLO en este caso de oposición directa.
- "irrelevante": el fragmento no menciona el tema de la afirmación en \
absoluto.

Por defecto, si tienes duda entre "respalda" y "contradice", responde \
"respalda" — contradecir es la excepción, no la opción segura.

Ejemplos:
1. Afirmación: "El proceso es rápido." Fragmento: "El proceso es rápido y \
eficiente." → respalda (dice lo mismo).
2. Afirmación: "El sistema no reduce el tiempo de trabajo." Fragmento: "El \
sistema reduce significativamente el tiempo de trabajo." → contradice \
(oposición directa: "no reduce" vs. "sí reduce").
3. Afirmación: "El modelo usa 768 dimensiones." Fragmento: "El dataset tiene \
300 ejemplos de entrenamiento." → irrelevante (temas distintos).

Responde ÚNICAMENTE un objeto JSON con la clave "stance"."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "stance": {"type": "string", "enum": ["contradice", "respalda", "irrelevante"]},
    },
    "required": ["stance"],
}


def _with_updates(output: EvidentiaOutput, **updates) -> EvidentiaOutput:
    data = output.model_dump()
    data.update(updates)
    return EvidentiaOutput(**data)


def check_stance(claim: str, chunk_text: str, client: LLMClient | None = None) -> str:
    """Clasifica un único fragmento frente a una afirmación. Ante cualquier
    falla, devuelve 'irrelevante' (no bloquea el flujo principal; esta es
    una verificación adicional, no la decisión primaria)."""
    client = client or get_client()
    user_prompt = f"Afirmación:\n{claim}\n\nFragmento:\n{chunk_text}"
    try:
        raw = generate_json(client, SYSTEM_PROMPT, user_prompt, RESPONSE_SCHEMA, schema_name="check_stance")
        stance = raw.get("stance")
        return stance if stance in {"contradice", "respalda", "irrelevante"} else "irrelevante"
    except (
        ValidationError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        requests.RequestException,
    ):
        return "irrelevante"


def check_contradiction(
    output: EvidentiaOutput, evidence: list[ScoredChunk], client: LLMClient | None = None
) -> EvidentiaOutput:
    """Veto quirúrgico: solo se activa cuando evaluate_evidence ya dijo
    'evidencia_suficiente' (el caso de mayor riesgo si está mal), y solo
    revisa los chunks CITADOS (no todos los recuperados), para no multiplicar
    el costo en llamadas al LLM."""
    if output.evidence_level != EvidenceLevel.SUFICIENTE or not output.sources:
        return output

    evidence_by_id = {sc.chunk.chunk_id: sc.chunk for sc in evidence}
    client = client or get_client()

    for source in output.sources:
        chunk = evidence_by_id.get(source.chunk_id)
        if chunk is None:
            continue
        if check_stance(output.claim, chunk.text, client=client) == "contradice":
            return _with_updates(
                output,
                evidence_level=EvidenceLevel.PARCIAL,
                needs_human_review=True,
                answer=(
                    f"{output.answer} [contradiction_check: el fragmento citado "
                    f"({source.chunk_id}) parece contradecir la afirmación; "
                    "se degrada a evidencia_parcial para revisión humana]"
                ),
            )

    return output
