"""Corre el banco de pruebas oficial (data/eval/test_cases.json, 25 casos) y
calcula métricas reales de recuperación y clasificación (Fase 4 del
anteproyecto, sección 12). A diferencia de scripts/demo.py y
scripts/demo_fresh.py, esto no es anecdótico: da un número agregado sobre
los 25 casos diseñados para cubrir las categorías pedidas.

Requiere LM Studio corriendo (ver README). Usa el corpus real
(data/processed/chunks.jsonl).

Uso: venv\\Scripts\\python.exe scripts\\run_eval.py
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
TEST_CASES_PATH = ROOT / "data" / "eval" / "test_cases.json"
TOP_K = 5

# Casos que no son afirmaciones de contenido verificable (pruebas de
# robustez de parámetros / flujo del orquestador) — se reportan aparte,
# no cuentan en las métricas de recuperación/clasificación.
PROCESS_ONLY_CASES = {"TH03", "TH04"}


def load_chunks() -> list[ChunkMetadata]:
    chunks = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(ChunkMetadata(**json.loads(line)))
    return chunks


def run_content_case(case: dict, retriever: HybridRetriever) -> dict:
    retrieved = retriever.search(case["question"], top_k=TOP_K)
    retrieved_doc_ids = {sc.chunk.document_id for sc in retrieved}
    expected_sources = set(case.get("expected_sources") or [])

    recall_hit = (
        None
        if not expected_sources
        else bool(expected_sources & retrieved_doc_ids)
    )

    result = evaluate_claim(case["id"], case["question"], retrieved)

    expected_level = case.get("expected_evidence_level")
    classification_match = (
        None if expected_level is None else result.evidence_level.value == expected_level
    )

    # chunk_id convention is "{document_id}_{n}", so document_id is the prefix.
    cited_doc_ids = {s.chunk_id.split("_")[0] for s in result.sources}

    return {
        "id": case["id"],
        "category": case["category"],
        "recall_hit": recall_hit,
        "retrieved_doc_ids": sorted(retrieved_doc_ids),
        "expected_sources": sorted(expected_sources),
        "expected_evidence_level": expected_level,
        "actual_evidence_level": result.evidence_level.value,
        "classification_match": classification_match,
        "cited_doc_ids": sorted(cited_doc_ids),
        "needs_human_review": result.needs_human_review,
        "answer": result.answer,
    }


def run_th03(retriever: HybridRetriever) -> dict:
    n_chunks = len(retriever.lexical)
    results = retriever.search("prueba de parámetros fuera de rango", top_k=500)
    clamped_to_corpus = len(results) <= n_chunks
    hard_cap_enforced = len(results) <= 20  # anteproyecto: top_k <= 20
    return {
        "id": "TH03",
        "n_results_for_top_k_500": len(results),
        "corpus_size": n_chunks,
        "clamped_to_corpus_size": clamped_to_corpus,
        "hard_cap_top_k_20_enforced": hard_cap_enforced,
    }


def main():
    test_cases = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))
    chunks = load_chunks()
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)

    content_results = []
    process_results = []

    for case in test_cases:
        if case["id"] in PROCESS_ONLY_CASES:
            continue
        print(f"Evaluando {case['id']} ({case['category']})...")
        content_results.append(run_content_case(case, retriever))

    process_results.append(run_th03(retriever))

    print("\n" + "=" * 90)
    print("RESULTADOS DETALLADOS")
    print("=" * 90)
    for r in content_results:
        status = "✓" if r["classification_match"] else ("✗" if r["classification_match"] is not None else "?")
        recall_status = "✓" if r["recall_hit"] else ("✗" if r["recall_hit"] is not None else "-")
        print(
            f"[{r['id']}] recall={recall_status} clasificación={status} "
            f"esperado={r['expected_evidence_level']} real={r['actual_evidence_level']} "
            f"citó={r['cited_doc_ids']} esperaba={r['expected_sources']}"
        )

    print("\n--- TH03 (parámetros fuera de rango) ---")
    th03 = process_results[0]
    print(json.dumps(th03, indent=2, ensure_ascii=False))

    recall_cases = [r for r in content_results if r["recall_hit"] is not None]
    classification_cases = [r for r in content_results if r["classification_match"] is not None]
    recall_at_5 = sum(r["recall_hit"] for r in recall_cases) / len(recall_cases) if recall_cases else None
    classification_accuracy = (
        sum(r["classification_match"] for r in classification_cases) / len(classification_cases)
        if classification_cases
        else None
    )

    print("\n" + "=" * 90)
    print("RESUMEN")
    print("=" * 90)
    print(f"Casos de contenido evaluados: {len(content_results)}")
    print(f"Recall@{TOP_K} (documento esperado en el top-{TOP_K}): {recall_at_5:.2%} ({sum(r['recall_hit'] for r in recall_cases)}/{len(recall_cases)})")
    print(f"Exactitud de clasificación (evidence_level == esperado): {classification_accuracy:.2%} ({sum(r['classification_match'] for r in classification_cases)}/{len(classification_cases)})")
    print(f"TH03 — ¿respeta el límite duro top_k<=20 del anteproyecto?: {th03['hard_cap_top_k_20_enforced']}")

    with (ROOT / "logs" / "eval_results.json").open("w", encoding="utf-8") as f:
        json.dump(
            {"content_results": content_results, "process_results": process_results},
            f,
            indent=2,
            ensure_ascii=False,
        )
    print("\nResultados completos guardados en logs/eval_results.json")


if __name__ == "__main__":
    main()
