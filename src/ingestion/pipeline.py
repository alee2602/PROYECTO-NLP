from datetime import date
from pathlib import Path

from src.schemas.chunk import ChunkMetadata
from src.schemas.document import DocumentMetadata

from .chunker import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, chunk_pages
from .cleaner import clean_text, strip_repeated_lines
from .extractor import PageText, extract_text_by_page
from .pdf_loader import load_pdf


def ingest_document(
    path: str | Path,
    document_id: str,
    title: str,
    source: str,
    authors: list[str] | None = None,
    doi: str | None = None,
    publication_year: int | None = None,
    version: str = "1",
    license: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> tuple[DocumentMetadata, list[ChunkMetadata]]:
    """Run the full ingestion pipeline for one PDF: load -> extract ->
    clean -> chunk -> attach metadata. Returns the document metadata and
    its chunks, ready to be embedded and indexed (Fase 2 siguiente paso)."""
    doc = load_pdf(path)
    try:
        pages = extract_text_by_page(doc)
    finally:
        doc.close()

    pages = strip_repeated_lines(pages)
    pages = [PageText(page=p.page, text=clean_text(p.text)) for p in pages]
    raw_chunks = chunk_pages(pages, chunk_size=chunk_size, overlap=overlap)

    document_meta = DocumentMetadata(
        document_id=document_id,
        title=title,
        authors=authors or [],
        source=source,
        doi=doi,
        publication_year=publication_year,
        version=version,
        license=license,
        ingestion_date=date.today(),
    )

    chunks = [
        ChunkMetadata(
            chunk_id=f"{document_id}_{i:04d}",
            document_id=document_id,
            text=raw_chunk.text,
            page=raw_chunk.page,
            section=raw_chunk.section,
            source=source,
            version=version,
            doi=doi,
            publication_year=publication_year,
        )
        for i, raw_chunk in enumerate(raw_chunks)
    ]

    return document_meta, chunks
