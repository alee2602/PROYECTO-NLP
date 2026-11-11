from pathlib import Path

import pymupdf as fitz

MAX_SIZE_MB = 50
MAX_PAGES = 200


class PDFValidationError(Exception):
    pass


def _contains_embedded_javascript(doc: fitz.Document) -> bool:
    """SEC06: rechazo por contenido activo embebido. Se revisa la sintaxis
    de cada objeto PDF (vía xref_object, sin descomprimir streams binarios)
    en vez de buscar "/JavaScript" en los bytes crudos del archivo -- un
    escaneo de bytes crudo da falsos positivos reales: 2 de los 20
    documentos del corpus (D12, D15) contienen la subcadena "/JS" dentro de
    streams comprimidos (FlateDecode) sin relación alguna con JavaScript."""
    for xref in range(1, doc.xref_length()):
        try:
            obj = doc.xref_object(xref, compressed=False)
        except Exception:  # noqa: BLE001 - xref inválido o stream no inspeccionable
            continue
        if "/JavaScript" in obj:
            return True
    return False


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

    if _contains_embedded_javascript(doc):
        doc.close()
        raise PDFValidationError(f"PDF contains embedded JavaScript, rejected: {path}")

    if doc.is_encrypted:
        doc.close()
        raise PDFValidationError(f"Encrypted PDF not supported: {path}")
    if doc.page_count == 0:
        doc.close()
        raise PDFValidationError(f"PDF has no pages: {path}")
    if doc.page_count > MAX_PAGES:
        page_count = doc.page_count
        doc.close()
        raise PDFValidationError(
            f"PDF has too many pages ({page_count} > {MAX_PAGES}): {path}"
        )

    return doc
