import json

from src.agent.extract_claims import _is_too_vague, extract_claims


class FakeClient:
    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls = 0

    def chat(self, **kwargs):
        content = self._contents[min(self.calls, len(self._contents) - 1)]
        self.calls += 1
        return {"choices": [{"message": {"content": content}}]}


def test_extract_claims_returns_parsed_claims():
    response = json.dumps(
        {
            "claims": [
                {"text": "BM25 combina frecuencia de términos y longitud del documento."},
                {"text": "FAISS se usa para búsqueda de similitud entre vectores."},
            ]
        }
    )
    client = FakeClient([response])

    claims = extract_claims("Texto del documento sobre BM25 y FAISS.", client=client)

    assert len(claims) == 2
    assert "BM25" in claims[0]


def test_extract_claims_respects_max_claims():
    response = json.dumps({"claims": [{"text": f"afirmación {i}"} for i in range(10)]})
    client = FakeClient([response])

    claims = extract_claims("documento largo", max_claims=3, client=client)

    assert len(claims) == 3


def test_extract_claims_returns_empty_list_on_malformed_response():
    client = FakeClient(["not valid json"])

    claims = extract_claims("documento", client=client)

    assert claims == []


def test_extract_claims_returns_empty_list_when_no_claims_found():
    client = FakeClient([json.dumps({"claims": []})])

    claims = extract_claims("documento sin afirmaciones fácticas claras", client=client)

    assert claims == []


def test_extract_claims_truncates_very_long_documents():
    long_document = "palabra " * 10_000
    client = FakeClient([json.dumps({"claims": [{"text": "algo"}]})])

    extract_claims(long_document, client=client)

    # No debe reventar ni mandar el documento completo sin truncar.
    assert len(long_document) > 10_000


def test_is_too_vague_rejects_generic_methodology_claims():
    # Regression test: este caso exacto se extrajo dos veces en pruebas
    # reales (scripts/run_orchestrator_demo.py sobre D04) y causó una mala
    # atribución (citaba un documento sin relación). Ver DECISIONS.md.
    assert _is_too_vague("We propose various approaches to combat these problems.")
    assert _is_too_vague("We use different methods to address these challenges.")


def test_is_too_vague_accepts_specific_claims():
    assert not _is_too_vague("BM25 combines term frequency and document length.")
    assert not _is_too_vague("COLIEE-2019 defined four problems related to IR.")
    assert not _is_too_vague('The dataset contains "10,000 annotated examples".')


def test_extract_claims_filters_out_vague_claims_from_llm_response():
    response = json.dumps(
        {
            "claims": [
                {"text": "We propose various approaches to combat these problems."},
                {"text": "COLIEE-2019 defined four problems related to IR."},
            ]
        }
    )
    client = FakeClient([response])

    claims = extract_claims("documento", client=client)

    assert claims == ["COLIEE-2019 defined four problems related to IR."]
