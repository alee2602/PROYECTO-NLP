from unittest.mock import Mock, patch

import requests

from src.agent.search_metadata import search_metadata

CROSSREF_ITEM = {
    "title": ["Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"],
    "author": [{"given": "Patrick", "family": "Lewis"}, {"given": "Ethan", "family": "Perez"}],
    "DOI": "10.1234/example",
    "published": {"date-parts": [[2020]]},
    "container-title": ["NeurIPS"],
}


def _mock_response(status_code=200, json_data=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.raise_for_status = Mock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    return response


def test_search_by_doi_returns_formatted_metadata():
    with patch("src.agent.search_metadata.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"message": CROSSREF_ITEM})

        result = search_metadata(doi="10.1234/example")

    assert result["title"] == "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
    assert "Patrick Lewis" in result["authors"]
    assert result["publication_year"] == 2020
    assert result["doi"] == "10.1234/example"


def test_search_by_doi_returns_none_on_404():
    with patch("src.agent.search_metadata.requests.get") as mock_get:
        mock_get.return_value = _mock_response(status_code=404)

        result = search_metadata(doi="10.9999/does-not-exist")

    assert result is None


def test_search_by_title_returns_first_match():
    with patch("src.agent.search_metadata.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"message": {"items": [CROSSREF_ITEM]}})

        result = search_metadata(title="Retrieval-Augmented Generation")

    assert result["doi"] == "10.1234/example"


def test_search_by_title_returns_none_when_no_items():
    with patch("src.agent.search_metadata.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"message": {"items": []}})

        result = search_metadata(title="Nonexistent paper title")

    assert result is None


def test_search_returns_none_without_doi_or_title():
    assert search_metadata() is None


def test_search_degrades_gracefully_on_network_error():
    with patch("src.agent.search_metadata.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("network unreachable")

        result = search_metadata(doi="10.1234/example")

    assert result is None
