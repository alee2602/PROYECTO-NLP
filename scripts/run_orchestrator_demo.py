"""Corre el flujo agéntico completo (extract_claims -> search_evidence ->
evaluate_evidence/validate_citations, con refinamiento) sobre un documento
real del corpus, evaluando sus afirmaciones contra TODO el corpus (no solo
contra sí mismo) — así es como debe funcionar el sistema real.

Uso: venv\\Scripts\\python.exe scripts\\run_orchestrator_demo.py [DOCUMENT_ID]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.orchestrator import run_pipeline  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.schemas.chunk import ChunkMetadata  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
DEFAULT_DOCUMENT_ID = "D04"
MAX_CLAIMS = 6


def load_chunks() -> list[ChunkMetadata]:
    chunks = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(ChunkMetadata(**json.loads(line)))
    return chunks


def main():
    document_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DOCUMENT_ID
    all_chunks = load_chunks()

    retriever = HybridRetriever()
    retriever.index_chunks(all_chunks)

    doc_chunks = [c for c in all_chunks if c.document_id == document_id]
    document_text = "\n\n".join(c.text for c in doc_chunks[:6])
    print(f"Documento {document_id}: usando {min(6, len(doc_chunks))} de {len(doc_chunks)} chunks como texto fuente.\n")

    results = run_pipeline(document_text, retriever=retriever, max_claims=MAX_CLAIMS)

    print(f"Afirmaciones extraídas y evaluadas: {len(results)}\n")
    for r in results:
        print("=" * 90)
        print(f"Afirmación: {r.claim}")
        print(r.model_dump_json(indent=2))
        print()


if __name__ == "__main__":
    main()
