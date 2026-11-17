import pymupdf
import pytest

from app.helpers import (
    document_text,
    ingest_upload,
    load_corpus_chunks,
    new_owner_id,
    result_rows,
    summary,
)
from src.ingestion.pdf_loader import PDFValidationError
from src.schemas.output import EvidentiaOutput, SourceRef


def _pdf_bytes(text="BM25 is a ranking function used in retrieval. " * 20) -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_textbox((50, 50, 550, 750), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_upload_chunks_are_owned_by_session():
    owner = new_owner_id()
    doc_id, chunks = ingest_upload(_pdf_bytes(), "paper.pdf", owner)
    assert chunks and all(c.owner_id == owner for c in chunks)
    assert document_text(chunks, doc_id)


def test_invalid_upload_is_rejected():
    with pytest.raises(PDFValidationError):
        ingest_upload(b"MZ not a pdf", "x.pdf", "sess_x")


def test_missing_corpus_returns_empty(tmp_path):
    assert load_corpus_chunks(tmp_path / "nope.jsonl") == []


def test_result_rows_and_summary():
    ok = EvidentiaOutput(
        answer="a", sources=[SourceRef(source="D01", page=2, chunk_id="D01_0000")],
        abstained=False, needs_human_review=False, claim_id="C0", claim="x",
        evidence_level="evidencia_suficiente",
    )
    none = EvidentiaOutput(
        answer="a", abstained=True, needs_human_review=True, claim_id="C1", claim="y",
        evidence_level="evidencia_no_localizada",
    )
    rows = result_rows([ok, none])
    assert rows[0]["Fuentes"] == "D01 p.2" and rows[1]["Fuentes"] == "—"
    assert summary([ok, none]) == {"total": 2, "suficiente": 1, "parcial": 0, "no_localizada": 1, "revision": 1}
