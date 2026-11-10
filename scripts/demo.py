"""Demo visible de punta a punta: toma varias afirmaciones (algunas con
respaldo real, algunas falsas, una sin respuesta posible), recupera
evidencia del corpus real y la manda al LLM para clasificar. Imprime cada
paso para poder revisar manualmente si el sistema está razonando bien.

Requiere: haber corrido scripts/build_corpus.py antes, y LM Studio con
servidor corriendo (ver README, sección "Usar el modelo generativo").

Uso:
    venv\\Scripts\\python.exe scripts\\demo.py
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

# Afirmaciones de ejemplo, no las 25 oficiales del banco de pruebas —
# elegidas para mostrar los tres comportamientos clave: respaldo correcto,
# respaldo falso/engañoso, y abstención por falta de evidencia.
DEMO_CLAIMS = [
    {
        "id": "DEMO01",
        "claim": "BM25 es una función de ranking que combina frecuencia de "
        "términos y longitud del documento para recuperación léxica.",
        "expect": "evidencia_suficiente (es una definición estándar y correcta)",
    },
    {
        "id": "DEMO02",
        "claim": "FAISS fue desarrollado por Google para búsqueda de similitud "
        "de vectores.",
        "expect": "evidencia_no_localizada o contradicción (FAISS es de Meta/Facebook, no Google)",
    },
    {
        "id": "DEMO03",
        "claim": "Los ataques de inyección de prompt en LLMs son completamente "
        "imposibles de detectar con las técnicas actuales.",
        "expect": "evidencia_no_localizada o evidencia_parcial (afirmación exagerada/absoluta)",
    },
    {
        "id": "DEMO04",
        "claim": "El framework RAGAS permite evaluar sistemas RAG sin necesitar "
        "anotaciones humanas para cada respuesta.",
        "expect": "evidencia_suficiente o parcial, según el paper de RAGAS (D09 aprox.)",
    },
]


def load_chunks() -> list[ChunkMetadata]:
    if not CHUNKS_PATH.exists():
        print(f"No existe {CHUNKS_PATH}. Corre primero: scripts\\build_corpus.py")
        sys.exit(1)
    chunks = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(ChunkMetadata(**json.loads(line)))
    return chunks


def main():
    chunks = load_chunks()
    print(f"Corpus cargado: {len(chunks)} chunks\n")

    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    for item in DEMO_CLAIMS:
        print("=" * 90)
        print(f"[{item['id']}] Afirmación: {item['claim']}")
        print(f"Esperado (referencia humana): {item['expect']}")
        print("-" * 90)

        retrieved = retriever.search(item["claim"], top_k=5)
        print("Evidencia recuperada (top-5):")
        for r in retrieved:
            snippet = r.chunk.text[:150].replace("\n", " ")
            print(f"  [{r.score:.3f}] {r.chunk.document_id} p.{r.chunk.page} | {snippet}...")

        result = evaluate_claim(item["id"], item["claim"], retrieved)

        print("\nResultado del LLM (evaluate_evidence):")
        print(result.model_dump_json(indent=2))
        print()


if __name__ == "__main__":
    main()
