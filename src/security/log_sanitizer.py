import hashlib
import re

# SEC07 (anteproyecto sección 13): los logs de eventos no deben contener
# datos personales en texto plano. El anteproyecto menciona "regex + spaCy
# NER" como mitigación -- spaCy quedó bloqueado en este entorno por el
# Control de aplicaciones de Windows incluso instalándolo vía conda (una
# dependencia nativa más profunda de thinc, no solo de spaCy mismo; ver
# DECISIONS.md), así que por ahora la sanitización es solo por regex
# (correos, teléfonos). Detectar nombres propios sin NER es un gap conocido
# y documentado, no una limitación oculta.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}\b")

_REDACTED_EMAIL = "[EMAIL_REDACTADO]"
_REDACTED_PHONE = "[TELEFONO_REDACTADO]"


def sanitize_for_log(text: str) -> str:
    """Reemplaza patrones de datos personales conocidos antes de escribir
    texto en un log de eventos. No es exhaustivo (ver nota de módulo sobre
    spaCy) -- cubre correos y teléfonos, los patrones más comunes y de
    mayor severidad si se filtran."""
    text = _EMAIL_RE.sub(_REDACTED_EMAIL, text)
    text = _PHONE_RE.sub(_REDACTED_PHONE, text)
    return text


def hash_for_log(text: str, length: int = 12) -> str:
    """Hash corto, no reversible, para loguear "qué texto fue" sin loguear
    el texto completo (ej. para deduplicar o correlacionar eventos)."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:length]
