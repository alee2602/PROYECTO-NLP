"""Variante de demo.py con afirmaciones NUEVAS, sobre documentos distintos a
los usados para ajustar el prompt (D01, D07, D08, D09 ya se usaron). El punto
es medir generalización real, no repetir casos ya calibrados.

Uso: venv\\Scripts\\python.exe scripts\\demo_fresh.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.evaluate_evidence import evaluate_claim  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.schemas.chunk import ChunkMetadata  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"

FRESH_CLAIMS = [
    {
        "id": "FRESH01",
        "claim": "MinHash es un método de hashing sensible a la localidad que "
        "lleva casi dos décadas siendo ampliamente utilizado.",
        "expect": "evidencia_suficiente (D06 lo confirma casi literal)",
    },
    {
        "id": "FRESH02",
        "claim": "El sistema SIR para búsqueda de imágenes similares en "
        "e-commerce no considera la eficiencia de las consultas, solo la "
        "precisión de búsqueda.",
        "expect": "contradicho -> evidencia_parcial (D05 optimiza AMBOS: precisión Y eficiencia)",
    },
    {
        "id": "FRESH03",
        "claim": "El paper sobre aumento cognitivo contextual reporta una "
        "mejora del 45% en tiempos de respuesta de usuarios en pruebas A/B.",
        "expect": "evidencia_no_localizada (cifra inventada, probablemente no aparece)",
    },
    {
        "id": "FRESH04",
        "claim": "La revisión de literatura automatizada combina técnicas de "
        "NLP con generación aumentada por recuperación basada en LLMs.",
        "expect": "evidencia_suficiente (es básicamente el título de D02)",
    },
]


def load_chunks() -> list[ChunkMetadata]:
    chunks = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(ChunkMetadata(**json.loads(line)))
    return chunks


def main():
    chunks = load_chunks()
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    for item in FRESH_CLAIMS:
        print("=" * 90)
        print(f"[{item['id']}] Afirmación: {item['claim']}")
        print(f"Esperado: {item['expect']}")
        print("-" * 90)

        retrieved = retriever.search(item["claim"], top_k=5)
        for r in retrieved:
            print(f"  [{r.score:.3f}] {r.chunk.document_id} p.{r.chunk.page} | {r.chunk.text[:90]}")

        result = evaluate_claim(item["id"], item["claim"], retrieved)
        print("\nResultado:")
        print(result.model_dump_json(indent=2))
        print()


if __name__ == "__main__":
    main()
