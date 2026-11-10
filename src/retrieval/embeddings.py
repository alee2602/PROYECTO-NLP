from functools import lru_cache

import numpy as np

# Anteproyecto sección 10: multilingüe (español/inglés), 384 dimensiones,
# tamaño reducido comparado con otros modelos de Sentence Transformers.
DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=2)
def _get_model(model_name: str = DEFAULT_MODEL_NAME):
    # Imported lazily: sentence-transformers/torch are heavy, and most of the
    # ingestion/index code doesn't need them loaded just to be imported.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str], model_name: str = DEFAULT_MODEL_NAME
) -> np.ndarray:
    """Embed a batch of texts, L2-normalized so inner product == cosine
    similarity (matches the FAISS IndexFlatIP used in src/retrieval/index.py)."""
    model = _get_model(model_name)
    embeddings = model.encode(
        texts, normalize_embeddings=True, convert_to_numpy=True
    )
    return np.asarray(embeddings, dtype="float32")
