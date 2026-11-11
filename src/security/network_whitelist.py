from urllib.parse import urlparse

# SEC04 (anteproyecto sección 13): el sistema solo debe hablar con los
# dominios externos que de verdad necesita (arXiv para el corpus, Crossref
# para metadatos bibliográficos) -- nunca con una URL arbitraria, aunque
# venga de una respuesta de API ya parseada (ej. el href de un <link> en el
# XML de arXiv).
ALLOWED_DOMAINS = {
    "export.arxiv.org",
    "arxiv.org",
    "api.crossref.org",
}


class DisallowedDomainError(Exception):
    """Se intentó una llamada de red a un dominio fuera de la lista blanca."""


def is_domain_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return host in ALLOWED_DOMAINS or any(host.endswith(f".{d}") for d in ALLOWED_DOMAINS)


def require_allowed_domain(url: str) -> None:
    if not is_domain_allowed(url):
        raise DisallowedDomainError(f"Dominio no permitido: {url!r}")
