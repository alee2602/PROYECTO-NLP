"""Agrega documentos distractores al corpus (D11 en adelante) SIN tocar
D01-D10 ni los IDs ya usados en data/eval/test_cases.json. El objetivo es
una prueba de escala honesta: ¿el Recall@5 de 100% medido con 10
documentos se sostiene cuando hay más candidatos compitiendo, algunos
deliberadamente parecidos a los temas existentes?

Uso: venv\\Scripts\\python.exe scripts\\add_corpus_documents.py
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

# Mezcla de distractores "cercanos" (mismo dominio que D01-D10, para que
# compitan de verdad en el ranking) y "lejanos" (temas distintos, para
# variar el corpus).
QUERIES = [
    "dense retrieval for open domain question answering",   # cercano a D03
    "legal judgment prediction deep learning",               # cercano a D04
    "hallucination detection large language models",         # cercano a D09
    "jailbreak attacks large language models",                # cercano a D07/D08
    "image classification convolutional neural networks",    # cercano a D01/D05
    "knowledge graph embeddings",                             # lejano
    "sentence embeddings contrastive learning",               # lejano
    "recommendation systems collaborative filtering",         # lejano
    "speech recognition deep learning",                       # lejano
    "graph neural networks",                                  # lejano
]
PAPERS_PER_QUERY = 1
CANDIDATES_PER_QUERY = 5
CORPUS_MAX_PAGES = 40
ARXIV_LICENSE = "arXiv.org perpetual, non-exclusive license"


def main():
    documents = json.loads((PROCESSED_DIR / "documents.json").read_text(encoding="utf-8"))
    all_chunks = []
    with (PROCESSED_DIR / "chunks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            all_chunks.append(json.loads(line))

    existing_ids = {d["document_id"] for d in documents}
    seen_arxiv_ids = {d["source"].split(":", 1)[-1] for d in documents}
    doc_index = max(int(d["document_id"][1:]) for d in documents) + 1

    for query in QUERIES:
        candidates = search_arxiv(query, max_results=CANDIDATES_PER_QUERY)
        accepted = False

        for paper in candidates:
            if accepted:
                break
            if paper.arxiv_id in seen_arxiv_ids:
                continue

            document_id = f"D{doc_index:02d}"
            pdf_path = RAW_DIR / f"{document_id}.pdf"

            try:
                download_pdf(paper.pdf_url, pdf_path)
                page_count = pymupdf.open(pdf_path).page_count
                if page_count > CORPUS_MAX_PAGES:
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
            accepted = True

        if not accepted:
            print(f"  (sin candidato aceptable para: {query})")

    (PROCESSED_DIR / "documents.json").write_text(
        json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (PROCESSED_DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    new_docs = [d for d in documents if d["document_id"] not in existing_ids]
    print(f"\nAgregados {len(new_docs)} documentos nuevos. Total corpus: {len(documents)} documentos, {len(all_chunks)} chunks.")


if __name__ == "__main__":
    main()
