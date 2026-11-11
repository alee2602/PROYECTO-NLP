import pytest

from src.security.network_whitelist import DisallowedDomainError, is_domain_allowed, require_allowed_domain


def test_allows_arxiv_domains():
    assert is_domain_allowed("https://export.arxiv.org/api/query") is True
    assert is_domain_allowed("https://arxiv.org/pdf/2502.13141v2") is True


def test_allows_crossref_domain():
    assert is_domain_allowed("https://api.crossref.org/works/10.1234/abcd") is True


def test_rejects_arbitrary_domain():
    """SEC04 (anteproyecto sección 13): el sistema nunca debe hablar con un
    dominio fuera de la lista blanca, aunque la URL venga de una respuesta
    de API ya parseada."""
    assert is_domain_allowed("https://attacker.example.com/steal") is False


def test_rejects_lookalike_domain():
    assert is_domain_allowed("https://arxiv.org.attacker.example.com/pdf") is False


def test_require_allowed_domain_raises_on_disallowed():
    with pytest.raises(DisallowedDomainError):
        require_allowed_domain("https://attacker.example.com/steal")


def test_require_allowed_domain_passes_silently_when_allowed():
    require_allowed_domain("https://export.arxiv.org/api/query")
