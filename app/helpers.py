"""Lógica de la interfaz sin dependencia de Streamlit (para poder probarla)."""

import json
import os
import tempfile
import uuid
from pathlib import Path

import requests

from src.ingestion.pipeline import ingest_document
from src.schemas.chunk import ChunkMetadata
from src.schemas.output import EvidenceLevel, EvidentiaOutput

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
DOCUMENTS_PATH = ROOT / "data" / "processed" / "documents.json"

LEVEL_LABELS = {
    EvidenceLevel.SUFICIENTE: ("Evidencia suficiente", "success"),
    EvidenceLevel.PARCIAL: ("Evidencia parcial", "warning"),
    EvidenceLevel.NO_LOCALIZADA: ("Evidencia no localizada", "error"),
}


def new_owner_id() -> str:
    """Identidad de sesión: los PDFs subidos solo se recuperan con este id."""
    return f"sess_{uuid.uuid4().hex[:10]}"


def load_corpus_chunks(path: Path = CHUNKS_PATH) -> list[ChunkMetadata]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [ChunkMetadata(**json.loads(line)) for line in f if line.strip()]


def load_corpus_documents(path: Path = DOCUMENTS_PATH) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else list(data.values())


def ingest_upload(
    data: bytes, filename: str, owner_id: str
) -> tuple[str, list[ChunkMetadata]]:
    """Valida e ingesta un PDF subido. Lanza PDFValidationError si se rechaza
    (SEC06). Los chunks quedan asociados a owner_id (SEC03)."""
    document_id = f"U{uuid.uuid4().hex[:6].upper()}"
    # ignore_cleanup_errors: en Windows, cuando fitz.open() falla al parsear
    # un PDF inválido, MuPDF puede tardar en liberar el handle del archivo;
    # sin esto, el cleanup del TemporaryDirectory lanza PermissionError justo
    # cuando lo que queríamos reportar era el PDFValidationError original.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = Path(tmp) / "upload.pdf"
        path.write_bytes(data)
        _, chunks = ingest_document(
            path, document_id=document_id, title=filename, source=filename
        )
    chunks = [c.model_copy(update={"owner_id": owner_id}) for c in chunks]
    return document_id, chunks


def document_text(chunks: list[ChunkMetadata], document_id: str, max_chunks: int = 6) -> str:
    own = [c for c in chunks if c.document_id == document_id]
    return "\n\n".join(c.text for c in own[:max_chunks])


def result_rows(results: list[EvidentiaOutput]) -> list[dict]:
    return [
        {
            "ID": r.claim_id,
            "Afirmación": r.claim,
            "Nivel": LEVEL_LABELS[r.evidence_level][0],
            "Revisión humana": "Sí" if r.needs_human_review else "No",
            "Fuentes": ", ".join(f"{s.source} p.{s.page}" for s in r.sources) or "—",
        }
        for r in results
    ]


def summary(results: list[EvidentiaOutput]) -> dict:
    return {
        "total": len(results),
        "suficiente": sum(r.evidence_level == EvidenceLevel.SUFICIENTE for r in results),
        "parcial": sum(r.evidence_level == EvidenceLevel.PARCIAL for r in results),
        "no_localizada": sum(r.evidence_level == EvidenceLevel.NO_LOCALIZADA for r in results),
        "revision": sum(r.needs_human_review for r in results),
    }


def llm_status() -> tuple[bool, str]:
    base = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1").rstrip("/")
    try:
        r = requests.get(f"{base}/models", timeout=3)
        r.raise_for_status()
        return True, os.getenv("LLM_MODEL", "local-model")
    except requests.RequestException:
        return False, base
