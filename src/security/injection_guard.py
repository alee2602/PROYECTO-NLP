import re

# SEC01/SEC02 (anteproyecto sección 13): patrones de inyección de instrucciones
# dentro de texto que debería tratarse solo como dato (la afirmación del
# usuario, o el contenido de un documento recuperado) -- ES/EN, no exhaustivo,
# pensado para capturar los intentos más comunes sin depender de que el LLM
# "se dé cuenta" por sí solo (mismo principio que validate_citations: verificar
# con código, no confiar en que el modelo resista por instrucción de prompt).
_INJECTION_PATTERNS = [
    r"ignora[s]?\s+(tus|todas\s+las|las|cualquier)\s+instruccion",
    r"ignore\s+(your|all|previous|the)\s+instructions?",
    r"disregard\s+(the|all|your|previous)\s+instructions?",
    r"olvida[s]?\s+(tus|las|todas\s+las)\s+instruccion",
    r"forget\s+(your|all|previous)\s+instructions?",
    r"clasifica\s+(esto|esta\s+afirmaci[oó]n|todo)\s+como\s+evidencia\s+suficiente",
    r"classify\s+(this|everything|it)\s+as\s+sufficient\s+evidence",
    r"responde\s+que\s+(esta\s+afirmaci[oó]n\s+)?est[aá]\s+respaldada",
    r"you\s+are\s+now\s+",
    r"act[uú]a\s+como\s+",
    r"system\s+prompt",
    r"siempre\s+responde\s+",
    r"always\s+(answer|respond|classify)\s+",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def detect_injection(text: str) -> bool:
    """True si el texto contiene un patrón típico de intento de manipular
    las instrucciones del sistema (inyección directa SEC01, o texto
    incrustado en un documento que intenta lo mismo, SEC02)."""
    return any(pattern.search(text) for pattern in _COMPILED_PATTERNS)
