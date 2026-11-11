"""Límites duros de parámetros (anteproyecto sección 11: top_k ≤ 20,
max_claims ≤ 15). Se aplican recortando (clamp) en los puntos de entrada, no
confiando en que quien llama pase valores razonables (ver TH03 en DECISIONS.md)."""

MAX_TOP_K = 20
MAX_CLAIMS = 15


def clamp(value: int, upper: int, lower: int = 1) -> int:
    return max(lower, min(int(value), upper))


def clamp_top_k(top_k: int) -> int:
    return clamp(top_k, MAX_TOP_K)


def clamp_max_claims(max_claims: int) -> int:
    return clamp(max_claims, MAX_CLAIMS)
