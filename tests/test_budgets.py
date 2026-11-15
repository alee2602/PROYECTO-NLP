import json

import pytest

import src.agent.orchestrator as orch
from src.agent.search_metadata import search_metadata
from src.security.budget import BudgetedClient, BudgetExceeded, ExternalCallBudget


class _Stub:
    def chat(self, **kw):
        return {"usage": {"total_tokens": 5}}


def test_budgeted_client_hard_stop_and_token_count():
    c = BudgetedClient(_Stub(), max_calls=2)
    c.chat()
    c.chat()
    assert c.total_tokens == 10
    with pytest.raises(BudgetExceeded):
        c.chat()


def test_external_call_budget():
    b = ExternalCallBudget(max_calls=2)
    assert b.consume() and b.consume() and not b.consume()


def test_search_metadata_respects_external_budget(monkeypatch):
    import src.agent.search_metadata as sm

    monkeypatch.setattr(sm.requests, "get", lambda *a, **k: pytest.fail("no debe llamar"))
    assert search_metadata(title="x", budget=ExternalCallBudget(max_calls=0)) is None


def test_search_metadata_rejects_malformed_doi(monkeypatch):
    import src.agent.search_metadata as sm

    monkeypatch.setattr(sm.requests, "get", lambda *a, **k: pytest.fail("no debe llamar"))
    assert search_metadata(doi="../../evil") is None
    assert search_metadata(doi="10.1234/../../x") is None


class _Client:
    def chat(self, **kw):
        if "extract" in json.dumps(kw["response_format"]):
            content = {"claims": [{"text": "A 5 B"}]}
        else:
            content = {"answer": "nada", "sources": [], "abstained": True,
                       "evidence_level": "evidencia_no_localizada", "needs_human_review": True}
        return {"choices": [{"message": {"content": json.dumps(content)}}]}


class _Retriever:
    def __init__(self):
        self.calls = 0

    def search(self, q, top_k=5, owner_id=None):
        self.calls += 1
        return []


def test_iteration_cap_per_claim(monkeypatch):
    monkeypatch.setattr(orch, "MAX_AGENT_ITERATIONS", 1)
    r = _Retriever()
    orch.run_pipeline("doc", r, client=_Client())
    assert r.calls == 1  # sin refinamiento: se respeta el tope


def test_default_allows_one_refinement():
    r = _Retriever()
    orch.run_pipeline("doc", r, client=_Client())
    assert r.calls == 2


def test_pipeline_returns_partial_results_when_llm_budget_exhausted(monkeypatch):
    monkeypatch.setattr(orch, "BudgetedClient", lambda c: BudgetedClient(c, max_calls=1))
    assert orch.run_pipeline("doc", _Retriever(), client=_Client()) == []
