"""Re-corre el pipeline de ingesta sobre los PDFs ya descargados en
data/raw/ (sin volver a pegarle a arXiv), usando la metadata existente en
documents.json. Util cuando se cambia algo en limpieza/chunking y hay que
regenerar chunks.jsonl sin depender de internet.

Uso:
    venv\\Scripts\\python.exe scripts\\reprocess_corpus.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.pipeline import ingest_document  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def main():
    docs = json.loads((PROCESSED_DIR / "documents.json").read_text(encoding="utf-8"))
    all_chunks = []

    for doc in docs:
        pdf_path = RAW_DIR / f"{doc['document_id']}.pdf"
        _, chunks = ingest_document(
            pdf_path,
            document_id=doc["document_id"],
            title=doc["title"],
            source=doc["source"],
            authors=doc["authors"],
            doi=doc["doi"],
            publication_year=doc["publication_year"],
            version=doc["version"],
            license=doc["license"],
        )
        all_chunks.extend(json.loads(c.model_dump_json()) for c in chunks)
        print(f"{doc['document_id']}: {len(chunks)} chunks")

    with (PROCESSED_DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_chunks)} chunks")


if __name__ == "__main__":
    main()
