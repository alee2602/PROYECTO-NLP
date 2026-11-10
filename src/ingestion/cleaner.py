import re
from collections import Counter

from .extractor import PageText


# Ligaduras tipográficas comunes en PDFs académicos (ej. "ﬁnd" en vez de
# "find"). Sin normalizar, estos caracteres llegaron a provocar un error en
# el motor de decodificación con grammar de LM Studio al generar JSON
# estructurado (ver DECISIONS.md).
_LIGATURES = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬆ": "st",
}


def clean_text(text: str) -> str:
    text = text.replace("­", "")  # soft hyphen
    for ligature, replacement in _LIGATURES.items():
        text = text.replace(ligature, replacement)
    text = re.sub(r"-\n(?=\w)", "", text)  # de-hyphenate words split across lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_repeated_lines(
    pages: list[PageText], min_repeat_ratio: float = 0.5, max_line_length: int = 120
) -> list[PageText]:
    """Remove lines that repeat across many pages (running headers/footers,
    page numbers) before they get treated as document content."""
    n_pages = len(pages)
    if n_pages < 3:
        return pages

    page_lines = [[line.strip() for line in p.text.split("\n") if line.strip()] for p in pages]
    line_counts: Counter[str] = Counter()
    for lines in page_lines:
        for line in set(lines):
            line_counts[line] += 1

    threshold = max(2, int(n_pages * min_repeat_ratio))
    repeated = {
        line
        for line, count in line_counts.items()
        if count >= threshold and len(line) <= max_line_length
    }

    return [
        PageText(page=p.page, text="\n".join(l for l in lines if l not in repeated))
        for p, lines in zip(pages, page_lines)
    ]
