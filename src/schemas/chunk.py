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
    # SEC03 (anteproyecto sección 13): None = documento compartido/público
    # (todo el corpus actual de arXiv). Un valor concreto restringe el chunk
    # a quien lo subió -- ver filtro en HybridRetriever.search.
    owner_id: str | None = None
