import re
from urllib.parse import quote

import requests

from src.security.budget import ExternalCallBudget
from src.security.network_whitelist import DisallowedDomainError, require_allowed_domain

CROSSREF_BASE_URL = "https://api.crossref.org/works"
DEFAULT_TIMEOUT = 10
_DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s]+$")


def _format_item(item: dict) -> dict:
    date_parts = (item.get("published", {}).get("date-parts") or [[None]])[0]
    return {
        "title": (item.get("title") or [None])[0],
        "authors": [
            f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author", [])
        ],
        "doi": item.get("DOI"),
        "publication_year": date_parts[0] if date_parts else None,
        "container_title": (item.get("container-title") or [None])[0],
    }


def search_metadata(
    doi: str | None = None,
    title: str | None = None,
    author: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    budget: ExternalCallBudget | None = None,
) -> dict | None:
    """search_metadata tool (anteproyecto sección 11): consulta metadatos
    bibliográficos en Crossref para contrastar una referencia (doi, title o
    author). Nunca se usa como evidencia textual (sección 7 del
    anteproyecto) — solo para verificar que una cita corresponde a un
    documento real. Degradación controlada: ante timeout/error de red,
    devuelve None en vez de propagar la excepción (anteproyecto TH05)."""
    if budget is not None and not budget.consume():
        return None  # tope de llamadas externas por afirmación (sección 13)
    try:
        if doi:
            # El DOI viene de texto no confiable: formato estricto y escapado.
            if not _DOI_RE.match(doi) or ".." in doi:
                return None
            url = f"{CROSSREF_BASE_URL}/{quote(doi, safe='/')}"
            require_allowed_domain(url)
            response = requests.get(url, timeout=timeout)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return _format_item(response.json()["message"])

        if title:
            require_allowed_domain(CROSSREF_BASE_URL)
            params = {"query.bibliographic": title, "rows": 1}
            if author:
                params["query.author"] = author
            response = requests.get(CROSSREF_BASE_URL, params=params, timeout=timeout)
            response.raise_for_status()
            items = response.json()["message"]["items"]
            return _format_item(items[0]) if items else None

        return None
    except (requests.RequestException, DisallowedDomainError):
        return None
