from src.agent.llm_client import LLMClient, generate_json


class FakeClient:
    def __init__(self, message: dict):
        self._message = message

    def chat(self, **kwargs):
        return {"choices": [{"message": self._message}]}


def test_generate_json_reads_content_field():
    client = FakeClient({"content": '{"answer": "ok"}'})
    assert generate_json(client, "sys", "user", {"type": "object"}) == {"answer": "ok"}


def test_generate_json_falls_back_to_reasoning_content_when_content_empty():
    """Regression test: modelos 'thinking' (ej. Qwen3.5) a veces devuelven
    content="" y ponen la respuesta real en reasoning_content. Ver
    DECISIONS.md — esto causaba que evaluate_claim fallara siempre con este
    tipo de modelo, sin importar el prompt."""
    client = FakeClient({"content": "", "reasoning_content": '{"stance": "respalda"}'})
    assert generate_json(client, "sys", "user", {"type": "object"}) == {"stance": "respalda"}


def test_generate_json_prefers_content_over_reasoning_content_when_both_present():
    client = FakeClient({"content": '{"answer": "from content"}', "reasoning_content": '{"answer": "from reasoning"}'})
    assert generate_json(client, "sys", "user", {"type": "object"}) == {"answer": "from content"}


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_chat_accumulates_token_usage_across_calls(monkeypatch):
    """Fase 4 (métricas operativas): LLMClient debe acumular el uso de
    tokens reportado por el servidor para poder estimar costo sin
    instrumentar cada llamador por separado."""
    responses = [
        {"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}},
        {"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 50, "completion_tokens": 10}},
    ]

    def fake_post(*args, **kwargs):
        return _FakeResponse(responses.pop(0))

    monkeypatch.setattr("src.agent.llm_client.requests.post", fake_post)

    client = LLMClient(base_url="http://fake", api_key="k")
    client.chat(messages=[])
    client.chat(messages=[])

    assert client.total_prompt_tokens == 150
    assert client.total_completion_tokens == 30
    assert client.total_calls == 2


def test_chat_handles_missing_usage_field(monkeypatch):
    def fake_post(*args, **kwargs):
        return _FakeResponse({"choices": [{"message": {"content": "{}"}}]})

    monkeypatch.setattr("src.agent.llm_client.requests.post", fake_post)

    client = LLMClient(base_url="http://fake", api_key="k")
    client.chat(messages=[])

    assert client.total_prompt_tokens == 0
    assert client.total_calls == 1
