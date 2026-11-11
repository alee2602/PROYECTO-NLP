import json

from src.security.event_log import log_event


def test_log_event_writes_sanitized_jsonl_line(tmp_path, monkeypatch):
    import src.security.event_log as event_log_module

    log_path = tmp_path / "events.log"
    monkeypatch.setattr(event_log_module, "LOG_PATH", log_path)

    log_event("evaluate_claim", claim_id="TC01", note="contacto: a@b.com", evidence_level="evidencia_suficiente")

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "evaluate_claim"
    assert record["claim_id"] == "TC01"
    assert "a@b.com" not in record["note"]
    assert "timestamp" in record


def test_log_event_appends_across_multiple_calls(tmp_path, monkeypatch):
    import src.security.event_log as event_log_module

    log_path = tmp_path / "events.log"
    monkeypatch.setattr(event_log_module, "LOG_PATH", log_path)

    log_event("evento_a")
    log_event("evento_b")

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
