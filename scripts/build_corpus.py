"""Arma el corpus inicial de Evidentia (D01-D10): descarga papers de arXiv
sobre los temas técnicos del propio proyecto, los procesa con el pipeline de
ingesta, y guarda documentos + chunks en data/processed/ listos para indexar.

Uso:
    venv\\Scripts\\python.exe scripts\\build_corpus.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf  # noqa: E402

from src.ingestion.arxiv_source import download_pdf, search_arxiv  # noqa: E402
from src.ingestion.pdf_loader import PDFValidationError  # noqa: E402
from src.ingestion.pipeline import ingest_document  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# Temas ligados al propio dominio técnico del proyecto (RAG, recuperación,
# seguridad de LLMs, evaluación) — fácil de conseguir vía arXiv, fácil de
# validar manualmente porque el equipo ya lo estudia en el curso.
QUERIES = [
    "retrieval augmented generation for knowledge intensive NLP",
    "BM25 probabilistic relevance framework information retrieval",
    "FAISS billion scale similarity search",
    "prompt injection attacks large language models",
    "retrieval augmented generation evaluation metrics",
]
PAPERS_PER_QUERY = 2
CANDIDATES_PER_QUERY = 5  # buffer for duplicates/oversized papers
CORPUS_MAX_PAGES = 40  # keep the MVP corpus to paper-length docs, not theses
ARXIV_LICENSE = "arXiv.org perpetual, non-exclusive license"


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    documents = []
    all_chunks = []
    doc_index = 1
    seen_arxiv_ids: set[str] = set()

    for query in QUERIES:
        candidates = search_arxiv(query, max_results=CANDIDATES_PER_QUERY)
        accepted_for_query = 0

        for paper in candidates:
            if accepted_for_query >= PAPERS_PER_QUERY:
                break
            if paper.arxiv_id in seen_arxiv_ids:
                print(f"  (dup, skip) {paper.title[:80]}")
                continue

            document_id = f"D{doc_index:02d}"
            pdf_path = RAW_DIR / f"{document_id}.pdf"

            try:
                download_pdf(paper.pdf_url, pdf_path)
                page_count = pymupdf.open(pdf_path).page_count
                if page_count > CORPUS_MAX_PAGES:
                    print(f"  (too long, {page_count}p, skip) {paper.title[:70]}")
                    pdf_path.unlink()
                    continue

                publication_year = int(paper.published[:4]) if paper.published else None
                document_meta, chunks = ingest_document(
                    pdf_path,
                    document_id=document_id,
                    title=paper.title,
                    source=f"arXiv:{paper.arxiv_id}",
                    authors=paper.authors,
                    doi=None,
                    publication_year=publication_year,
                    version="1",
                    license=ARXIV_LICENSE,
                )
            except (PDFValidationError, Exception) as exc:  # noqa: BLE001
                print(f"  SKIPPED ({type(exc).__name__}: {exc})")
                if pdf_path.exists():
                    pdf_path.unlink()
                continue

            seen_arxiv_ids.add(paper.arxiv_id)
            documents.append(json.loads(document_meta.model_dump_json()))
            all_chunks.extend(json.loads(c.model_dump_json()) for c in chunks)
            print(f"[{document_id}] {paper.title[:80]} -> {len(chunks)} chunks")
            doc_index += 1
            accepted_for_query += 1

    (PROCESSED_DIR / "documents.json").write_text(
        json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (PROCESSED_DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\nListo: {len(documents)} documentos, {len(all_chunks)} chunks.")
    print(f"Guardado en {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
