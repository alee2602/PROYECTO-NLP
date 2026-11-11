import json
import re

import requests
from pydantic import ValidationError

from src.limits import clamp_max_claims

from .llm_client import LLMClient, generate_json, get_client

# Filtro determinístico de vaguedad (no confiado al LLM, ver DECISIONS.md:
# instrucciones de prompt por sí solas no bastaron — un ejemplo casi idéntico
# al del prompt ("various approaches/strategies to combat/solve problems")
# se volvió a extraer de todas formas). Patrones de meta-comentario genérico
# sobre metodología, sin ningún dato/nombre/cifra específicos.
_VAGUE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(various|different|several|multiple)\s+(approaches?|methods?|strategies|techniques)\b",
        r"\bpropose\w*\s+(various|different|several|multiple|a\s+range\s+of)\b",
        r"\b(combat|address|tackle|solve)\s+(these|those|such)\s+(problems?|challenges?|issues?)\b",
    ]
]

# Una afirmación "específica" suele traer al menos uno de estos: una cifra,
# un acrónimo/nombre propio de 2+ letras mayúsculas, o un término entre
# comillas. Si no trae NADA de esto y además matchea un patrón vago, se
# descarta.
_SPECIFICITY_RE = re.compile(r"\d|[A-Z]{2,}|\"[^\"]+\"")


def _is_too_vague(claim: str) -> bool:
    has_vague_pattern = any(p.search(claim) for p in _VAGUE_PATTERNS)
    has_specific_signal = bool(_SPECIFICITY_RE.search(claim))
    return has_vague_pattern and not has_specific_signal

# Límite conservador de caracteres de entrada: documento + prompt + schema
# deben caber en el contexto del modelo (ver DECISIONS.md: ya se encontró un
# "context length exceeded" real con solo 5 chunks de evidencia).
MAX_INPUT_CHARS = 10_000

SYSTEM_PROMPT = """Eres el componente extract_claims de Evidentia. Tu trabajo \
es identificar afirmaciones fácticas dentro de un documento académico, para \
que luego otro componente verifique si tienen respaldo documental.

Reglas:
- Una afirmación debe ser una oración fáctica y verificable (se puede \
confirmar o refutar contra evidencia), no una pregunta, no un título de \
sección, no una opinión subjetiva ni una instrucción.
- RECHAZA afirmaciones vagas o genéricas que no tengan un dato, nombre o \
hallazgo específico — frases como "proponemos varias estrategias para estos \
problemas" o "usamos distintos enfoques" NO son afirmaciones útiles, porque \
casi cualquier documento sobre el tema parecería "respaldarlas" sin que eso \
signifique nada. Evita pronombres ambiguos ("estos problemas", "este \
enfoque") sin un sustantivo concreto que los reemplace.
- Prioriza afirmaciones con un dato concreto y verificable: una cifra, un \
nombre propio, una definición técnica, un resultado específico, una fecha, \
el nombre de un método o dataset.
- Extrae el texto de la afirmación tal como aparece en el documento, o con \
mínima paráfrasis si hace falta para que sea una oración completa y \
autocontenida (entendible sin el resto del párrafo, reemplazando pronombres \
ambiguos por lo que refieren).
- No repitas la misma afirmación de dos formas distintas.
- Si el documento no tiene afirmaciones fácticas claras y específicas, \
devuelve una lista vacía — es preferible devolver pocas afirmaciones \
buenas que muchas vagas.
- Responde ÚNICAMENTE un objeto JSON con la clave "claims": una lista de \
objetos con la clave "text"."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string", "minLength": 1}},
                "required": ["text"],
            },
        }
    },
    "required": ["claims"],
}


def extract_claims(
    document_text: str, max_claims: int = 10, client: LLMClient | None = None
) -> list[str]:
    """extract_claims tool (anteproyecto sección 11): identifica hasta
    max_claims afirmaciones fácticas en el texto de un documento. Si falla
    la generación o la validación, devuelve lista vacía (degradación
    segura) en vez de propagar la excepción."""
    max_claims = clamp_max_claims(max_claims)
    client = client or get_client()
    truncated = document_text[:MAX_INPUT_CHARS]
    user_prompt = (
        f"Extrae hasta {max_claims} afirmaciones fácticas de este documento "
        f"(puede estar truncado):\n\n{truncated}"
    )

    try:
        raw = generate_json(
            client, SYSTEM_PROMPT, user_prompt, RESPONSE_SCHEMA, schema_name="extract_claims"
        )
        claims = [c["text"] for c in raw.get("claims", []) if c.get("text")]
        claims = [c for c in claims if not _is_too_vague(c)]
        return claims[:max_claims]
    except (
        ValidationError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        requests.RequestException,
    ):
        return []
