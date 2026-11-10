from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page: int
    section: str | None = None
    source: str
    version: str = "1"
    doi: str | None = None
    publication_year: int | None = None
