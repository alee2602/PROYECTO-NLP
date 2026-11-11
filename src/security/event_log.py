import json
from datetime import datetime, timezone
from pathlib import Path

from src.security.log_sanitizer import sanitize_for_log

LOG_PATH = Path("logs/events.log")


def log_event(event: str, **fields) -> None:
    """SEC07 (anteproyecto sección 13): registra un evento sanitizando
    cualquier campo de texto libre antes de escribir -- nunca se escribe
    texto sin pasar primero por sanitize_for_log (correos/teléfonos)."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    sanitized = {
        key: sanitize_for_log(value) if isinstance(value, str) else value
        for key, value in fields.items()
    }
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **sanitized,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
