import pymupdf as fitz
import pytest

from src.ingestion.chunker import chunk_pages
from src.ingestion.cleaner import clean_text, strip_repeated_lines
from src.ingestion.extractor import PageText, extract_text_by_page
from src.ingestion.pdf_loader import PDFValidationError, load_pdf
from src.ingestion.pipeline import ingest_document


def test_clean_text_dehyphenates_and_normalizes_whitespace():
    raw = "This is a hyphen-\nated word.   Extra   spaces.\n\n\n\nToo many breaks."
    cleaned = clean_text(raw)
    assert "hyphenated word" in cleaned
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_strip_repeated_lines_removes_running_header():
    pages = [
        PageText(page=i, text=f"Evidentia — Confidential\nBody text {i}\nPage {i}")
        for i in range(1, 6)
    ]
    cleaned = strip_repeated_lines(pages)
    for p in cleaned:
        assert "Evidentia — Confidential" not in p.text
        assert "Body text" in p.text


def test_strip_repeated_lines_keeps_short_documents_untouched():
    pages = [PageText(page=1, text="Header\nBody"), PageText(page=2, text="Header\nBody")]
    cleaned = strip_repeated_lines(pages)
    assert cleaned == pages


def test_chunk_pages_empty_returns_empty():
    assert chunk_pages([]) == []


def test_chunk_pages_respects_size_and_overlap():
    text = " ".join(f"word{i}" for i in range(1000))
    pages = [PageText(page=1, text=text)]
    chunks = chunk_pages(pages, chunk_size=450, overlap=80)

    assert len(chunks) > 1
    for chunk in chunks[:-1]:
        assert len(chunk.text.split()) == 450

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-80:] == second_words[:80]


def test_chunk_pages_tracks_source_page():
    pages = [
        PageText(page=1, text=" ".join(f"w{i}" for i in range(100))),
        PageText(page=2, text=" ".join(f"w{i}" for i in range(100, 200))),
    ]
    chunks = chunk_pages(pages, chunk_size=450, overlap=80)
    assert chunks[0].page == 1


def test_load_pdf_rejects_missing_file(tmp_path):
    with pytest.raises(PDFValidationError):
        load_pdf(tmp_path / "does_not_exist.pdf")


def test_load_pdf_rejects_non_pdf_extension(tmp_path):
    bogus = tmp_path / "not_a_pdf.txt"
    bogus.write_text("hello")
    with pytest.raises(PDFValidationError):
        load_pdf(bogus)


def _make_sample_pdf(path, pages_text: list[str]):
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_extract_text_by_page_roundtrip(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_sample_pdf(pdf_path, ["Hello page one", "Hello page two"])
    doc = load_pdf(pdf_path)
    try:
        pages = extract_text_by_page(doc)
    finally:
        doc.close()
    assert len(pages) == 2
    assert "Hello page one" in pages[0].text
    assert "Hello page two" in pages[1].text


def test_ingest_document_end_to_end(tmp_path):
    pdf_path = tmp_path / "doc01.pdf"
    body = " ".join(f"evidence{i}" for i in range(600))
    _make_sample_pdf(pdf_path, [body])

    document_meta, chunks = ingest_document(
        pdf_path,
        document_id="D01",
        title="Sample Paper",
        source="local-test",
        authors=["Doe, J."],
        doi="10.1234/example",
        publication_year=2024,
        license="CC-BY",
    )

    assert document_meta.document_id == "D01"
    assert len(chunks) >= 1
    assert all(c.document_id == "D01" for c in chunks)
    assert all(c.chunk_id.startswith("D01_") for c in chunks)
    assert chunks[0].page == 1
