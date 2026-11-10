from dataclasses import dataclass

import pymupdf as fitz


@dataclass
class PageText:
    page: int  # 1-indexed, matches citations shown to the user
    text: str


def extract_text_by_page(doc: fitz.Document) -> list[PageText]:
    return [
        PageText(page=i, text=page.get_text("text"))
        for i, page in enumerate(doc, start=1)
    ]
