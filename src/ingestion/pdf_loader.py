from pathlib import Path

import pymupdf as fitz

MAX_SIZE_MB = 50
MAX_PAGES = 200


class PDFValidationError(Exception):
    pass


def load_pdf(path: str | Path) -> fitz.Document:
    """Load and validate a PDF file. Raises PDFValidationError on any
    rejection reason (see anteproyecto sección 13, SEC06: archivo
    malicioso o inválido)."""
    path = Path(path)

    if not path.exists():
        raise PDFValidationError(f"File not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise PDFValidationError(f"Not a PDF file: {path}")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise PDFValidationError(
            f"File too large ({size_mb:.1f} MB > {MAX_SIZE_MB} MB): {path}"
        )

    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise PDFValidationError(f"Could not open PDF: {path} ({exc})") from exc

    if doc.is_encrypted:
        doc.close()
        raise PDFValidationError(f"Encrypted PDF not supported: {path}")
    if doc.page_count == 0:
        doc.close()
        raise PDFValidationError(f"PDF has no pages: {path}")
    if doc.page_count > MAX_PAGES:
        doc.close()
        raise PDFValidationError(
            f"PDF has too many pages ({doc.page_count} > {MAX_PAGES}): {path}"
        )

    return doc
