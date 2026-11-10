"""Manual smoke test: llama evaluate_claim contra el servidor de LM Studio
que esté corriendo en LLM_BASE_URL (default http://localhost:1234/v1).

Uso:
    venv\\Scripts\\python.exe scripts\\check_llm.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODEL_NAME = "qwen2.5-vl-7b-instruct"
os.environ.setdefault("LLM_MODEL", MODEL_NAME)

from src.agent.evaluate_evidence import evaluate_claim  # noqa: E402
from src.agent.llm_client import get_client  # noqa: E402
from src.retrieval.index import ScoredChunk  # noqa: E402
from src.schemas.chunk import ChunkMetadata  # noqa: E402


def main():
    evidence = [
        ScoredChunk(
            chunk=ChunkMetadata(
                chunk_id="D01_0007",
                document_id="D01",
                text=(
                    "FAISS (Facebook AI Similarity Search) es una biblioteca para "
                    "la búsqueda eficiente de similitud y agrupamiento de vectores "
                    "densos de alta dimensión, desarrollada por Meta AI."
                ),
                page=3,
                source="D01",
            ),
            score=0.91,
        )
    ]
    claim = "FAISS es una biblioteca para búsqueda de similitud entre vectores."

    client = get_client()
    result = evaluate_claim("SMOKE01", claim, evidence, client=client)

    print("--- Resultado ---")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
