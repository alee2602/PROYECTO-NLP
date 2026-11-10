from dataclasses import dataclass

from .extractor import PageText

# Word count is used as a proxy for token count (anteproyecto sección 10 asks
# for ~450 tokens / 80 overlap). This is an approximation, not the output of
# the embedding model's actual tokenizer — good enough for a first line base,
# revisit if retrieval quality suffers from chunk-size drift.
DEFAULT_CHUNK_SIZE = 450
DEFAULT_OVERLAP = 80
MIN_TRAILING_CHUNK_SIZE = 50


@dataclass
class RawChunk:
    text: str
    page: int
    section: str | None = None


def chunk_pages(
    pages: list[PageText],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[RawChunk]:
    word_page_pairs = [
        (word, page.page) for page in pages for word in page.text.split()
    ]
    if not word_page_pairs:
        return []

    step = max(chunk_size - overlap, 1)
    n = len(word_page_pairs)
    chunks: list[RawChunk] = []
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        window = word_page_pairs[start:end]
        chunks.append(RawChunk(text=" ".join(w for w, _ in window), page=window[0][1]))
        if end == n:
            break
        start += step

    if len(chunks) > 1 and len(chunks[-1].text.split()) < MIN_TRAILING_CHUNK_SIZE:
        last = chunks.pop()
        chunks[-1] = RawChunk(
            text=f"{chunks[-1].text} {last.text}", page=chunks[-1].page
        )

    return chunks
