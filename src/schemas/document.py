from datetime import date

from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    document_id: str
    title: str
    authors: list[str] = []
    source: str
    doi: str | None = None
    publication_year: int | None = None
    version: str = "1"
    license: str | None = None
    ingestion_date: date
