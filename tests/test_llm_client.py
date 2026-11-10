from src.agent.llm_client import generate_json


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
