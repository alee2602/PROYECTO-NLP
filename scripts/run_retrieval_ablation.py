"""Ablation de recuperación: mide Recall@5 por separado para (a) solo
semántico, (b) solo léxico (BM25), (c) híbrido SIN boost de identificadores,
(d) híbrido completo (lo que usa el sistema real) — contra los mismos 21
casos de contenido del banco de pruebas oficial.

El objetivo es saber si el Recall@5=100% del sistema completo es sólido o
es un artefacto de un truco específico (el boost de identificadores) que
podría no generalizar a documentos/afirmaciones nuevas. No usa LLM, solo
recuperación — corre rápido y sin necesitar LM Studio.

Uso: venv\\Scripts\\python.exe scripts\\run_retrieval_ablation.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.retrieval.lexical import LexicalIndex  # noqa: E402
from src.retrieval.retriever import SemanticRetriever  # noqa: E402
from src.schemas.chunk import ChunkMetadata  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOP_K = 5


def load_chunks() -> list[ChunkMetadata]:
    chunks = []
    with (ROOT / "data" / "processed" / "chunks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            chunks.append(ChunkMetadata(**json.loads(line)))
    return chunks


def main():
    test_cases = json.loads((ROOT / "data" / "eval" / "test_cases.json").read_text(encoding="utf-8"))
    cases_with_sources = [
        c for c in test_cases if c.get("expected_sources")
    ]
    chunks = load_chunks()

    semantic = SemanticRetriever()
    semantic.index_chunks(chunks)
    lexical = LexicalIndex()
    lexical.add(chunks)
    hybrid = HybridRetriever()
    hybrid.index_chunks(chunks)

    variants = {
        "solo_semantico": lambda q: {sc.chunk.document_id for sc in semantic.search(q, top_k=TOP_K)},
        "solo_lexico": lambda q: {sc.chunk.document_id for sc in lexical.search(q, top_k=TOP_K)},
        "hibrido_sin_boost": lambda q: {
            sc.chunk.document_id
            for sc in hybrid.search(q, top_k=TOP_K, use_identifier_boost=False)
        },
        "hibrido_completo": lambda q: {sc.chunk.document_id for sc in hybrid.search(q, top_k=TOP_K)},
    }

    results = {name: [] for name in variants}
    per_case_misses = {name: [] for name in variants}

    for case in cases_with_sources:
        expected = set(case["expected_sources"])
        for name, search_fn in variants.items():
            retrieved = search_fn(case["question"])
            hit = bool(expected & retrieved)
            results[name].append(hit)
            if not hit:
                per_case_misses[name].append((case["id"], case["category"], sorted(expected), sorted(retrieved)))

    print(f"Casos evaluados: {len(cases_with_sources)}\n")
    print(f"{'Variante':<20} {'Recall@5':>10}")
    print("-" * 32)
    for name, hits in results.items():
        recall = sum(hits) / len(hits)
        print(f"{name:<20} {recall:>9.1%}")

    print("\n--- Casos que fallan por variante ---")
    for name, misses in per_case_misses.items():
        print(f"\n{name}: {len(misses)} fallos")
        for case_id, category, expected, retrieved in misses:
            print(f"  [{case_id}] ({category}) esperaba={expected} recuperó={retrieved}")


if __name__ == "__main__":
    main()
