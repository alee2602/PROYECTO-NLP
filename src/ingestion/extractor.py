from dataclasses import dataclass

import pymupdf as fitz

# SEC02 (anteproyecto sección 13): texto con tamaño de fuente casi nulo o del
# mismo color que el fondo (blanco) es invisible para quien lee el PDF, pero
# get_text("text") lo extrae igual que texto normal -- un vector común de
# inyección indirecta (instrucciones ocultas dirigidas al LLM). Se detectan
# esos spans vía get_text("dict") y se remueven del texto plano antes de que
# lleguen al resto del pipeline.
_MIN_VISIBLE_FONT_SIZE = 1.0
_WHITE_RGB_INT = 0xFFFFFF


@dataclass
class PageText:
    page: int  # 1-indexed, matches citations shown to the user
    text: str


def extract_text_by_page(doc: fitz.Document) -> list[PageText]:
    return [
        PageText(page=i, text=_strip_invisible_text(page))
        for i, page in enumerate(doc, start=1)
    ]


def _strip_invisible_text(page: fitz.Page) -> str:
    text = page.get_text("text")
    for hidden in _invisible_spans_text(page):
        if hidden and hidden in text:
            text = text.replace(hidden, "")
    return text


def _invisible_spans_text(page: fitz.Page) -> list[str]:
    hidden = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if _is_invisible(span):
                    hidden.append(span.get("text", ""))
    return hidden


def _is_invisible(span: dict) -> bool:
    return (
        span.get("size", 0) < _MIN_VISIBLE_FONT_SIZE
        or span.get("color", 0) == _WHITE_RGB_INT
    )
