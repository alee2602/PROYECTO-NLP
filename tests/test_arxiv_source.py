import pytest

from src.ingestion.arxiv_source import download_pdf, extract_version
from src.security.network_whitelist import DisallowedDomainError


def test_extract_version_reads_suffix_from_arxiv_id():
    assert extract_version("2309.15217v2") == "2"
    assert extract_version("2506.06962v3") == "3"


def test_extract_version_defaults_to_1_without_suffix():
    assert extract_version("2309.15217") == "1"


def test_download_pdf_rejects_disallowed_domain(tmp_path):
    """SEC04 (anteproyecto sección 13): nunca se descarga nada de un
    dominio fuera de la lista blanca, ni siquiera se intenta la conexión."""
    with pytest.raises(DisallowedDomainError):
        download_pdf("https://attacker.example.com/malware.pdf", tmp_path / "out.pdf")
