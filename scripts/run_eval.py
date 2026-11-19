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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.evaluate_evidence import evaluate_claim  # noqa: E402
from src.agent.llm_client import get_client  # noqa: E402
from src.agent.orchestrator import run_pipeline  # noqa: E402
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

# Para casos con varios expected_sources, por defecto se exige recuperar
# TODOS (la afirmación es compuesta: cada documento respalda un hecho
# distinto, ej. TC12/TC14). La categoría "ambigua" es la excepción: ahí los
# varios expected_sources son alternativas plausibles, no un conjunto
# obligatorio (TC15 es deliberadamente vaga a propósito; cualquiera de las
# 4 fuentes listadas sería una recuperación razonable, no se espera que
# aparezcan las 4 en el top-5). Ver DECISIONS.md.
ANY_MATCH_CATEGORIES = {"ambigua"}


def load_chunks() -> list[ChunkMetadata]:
    chunks = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(ChunkMetadata(**json.loads(line)))
    return chunks


def _mrr_contribution(ranked_doc_ids: list[str], expected_sources: set[str]) -> float | None:
    """MRR clásico: 1/posición del primer documento esperado en el orden de
    recuperación, sin importar si el caso exige "any" o "all" (ese matiz es
    de recall_hit, no de MRR -- ver DECISIONS.md)."""
    if not expected_sources:
        return None
    for rank, doc_id in enumerate(ranked_doc_ids, start=1):
        if doc_id in expected_sources:
            return 1.0 / rank
    return 0.0


def run_content_case(case: dict, retriever: HybridRetriever, client) -> dict:
    search_start = time.perf_counter()
    retrieved = retriever.search(case["question"], top_k=TOP_K)
    search_latency_s = time.perf_counter() - search_start

    ranked_doc_ids = [sc.chunk.document_id for sc in retrieved]
    retrieved_doc_ids = set(ranked_doc_ids)
    expected_sources = set(case.get("expected_sources") or [])

    requires_all = len(expected_sources) > 1 and case["category"] not in ANY_MATCH_CATEGORIES
    if not expected_sources:
        recall_hit = None
    elif requires_all:
        recall_hit = expected_sources.issubset(retrieved_doc_ids)
    else:
        recall_hit = bool(expected_sources & retrieved_doc_ids)

    evaluate_start = time.perf_counter()
    result = evaluate_claim(case["id"], case["question"], retrieved, client=client)
    evaluate_latency_s = time.perf_counter() - evaluate_start

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
        "mrr": _mrr_contribution(ranked_doc_ids, expected_sources),
        "retrieved_doc_ids": sorted(retrieved_doc_ids),
        "expected_sources": sorted(expected_sources),
        "expected_evidence_level": expected_level,
        "actual_evidence_level": result.evidence_level.value,
        "classification_match": classification_match,
        "cited_doc_ids": sorted(cited_doc_ids),
        "needs_human_review": result.needs_human_review,
        "answer": result.answer,
        "search_latency_s": search_latency_s,
        "evaluate_latency_s": evaluate_latency_s,
    }


def _percentile(values: list[float], p: float) -> float:
    """Percentil simple por interpolación (sin depender de numpy)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


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


def run_th04(retriever: HybridRetriever, client) -> dict:
    """TH04 (anteproyecto sección 13 / SEC04): una afirmación sin respaldo
    real no debe hacer que el orquestador amplíe la búsqueda más allá del
    límite permitido ni termine en evidencia_suficiente sin evidencia --
    debe pedir confirmación humana. Usa run_pipeline (no evaluate_claim
    directo) porque es justo el límite de refinamiento del orquestador lo
    que se está probando, no la clasificación de un chunk ya recuperado."""
    document_text = "El método ZXQ-9000 reduce el error de traducción en un 87% según estudios recientes."
    results = run_pipeline(document_text, retriever=retriever, max_claims=1, client=client)
    result = results[0] if results else None
    ok = (
        result is not None
        and result.evidence_level.value != "evidencia_suficiente"
        and result.needs_human_review is True
    )
    return {
        "id": "TH04",
        "evidence_level": result.evidence_level.value if result else None,
        "needs_human_review": result.needs_human_review if result else None,
        "no_false_suficiente_and_requires_human_review": ok,
    }


def main():
    test_cases = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))
    chunks = load_chunks()
    retriever = HybridRetriever()
    retriever.index_chunks(chunks)
    client = get_client()

    content_results = []
    process_results = []

    for case in test_cases:
        if case["id"] in PROCESS_ONLY_CASES:
            continue
        print(f"Evaluando {case['id']} ({case['category']})...")
        content_results.append(run_content_case(case, retriever, client))

    process_results.append(run_th03(retriever))
    print("Evaluando TH04 (herramienta_confirmacion_humana)...")
    process_results.append(run_th04(retriever, client))

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

    print("\n--- TH04 (ampliación de búsqueda sin confirmación humana) ---")
    th04 = process_results[1]
    print(json.dumps(th04, indent=2, ensure_ascii=False))

    recall_cases = [r for r in content_results if r["recall_hit"] is not None]
    classification_cases = [r for r in content_results if r["classification_match"] is not None]
    recall_at_5 = sum(r["recall_hit"] for r in recall_cases) / len(recall_cases) if recall_cases else None
    classification_accuracy = (
        sum(r["classification_match"] for r in classification_cases) / len(classification_cases)
        if classification_cases
        else None
    )

    mrr_cases = [r for r in content_results if r["mrr"] is not None]
    mrr = sum(r["mrr"] for r in mrr_cases) / len(mrr_cases) if mrr_cases else None

    search_latencies = [r["search_latency_s"] for r in content_results]
    evaluate_latencies = [r["evaluate_latency_s"] for r in content_results]

    print("\n" + "=" * 90)
    print("RESUMEN")
    print("=" * 90)
    print(f"Casos de contenido evaluados: {len(content_results)}")
    print(f"Recall@{TOP_K} (documento esperado en el top-{TOP_K}): {recall_at_5:.2%} ({sum(r['recall_hit'] for r in recall_cases)}/{len(recall_cases)})")
    print(f"MRR: {mrr:.3f} ({len(mrr_cases)} casos con expected_sources)")
    print(f"Exactitud de clasificación (evidence_level == esperado): {classification_accuracy:.2%} ({sum(r['classification_match'] for r in classification_cases)}/{len(classification_cases)})")
    print(f"TH03 — ¿respeta el límite duro top_k<=20 del anteproyecto?: {th03['hard_cap_top_k_20_enforced']}")
    print(f"TH04 — ¿pide confirmación humana en vez de forzar evidencia_suficiente?: {th04['no_false_suficiente_and_requires_human_review']}")
    print(
        f"Latencia búsqueda (s) — media: {sum(search_latencies) / len(search_latencies):.3f}, "
        f"P95: {_percentile(search_latencies, 0.95):.3f}"
    )
    print(
        f"Latencia evaluate_claim (s) — media: {sum(evaluate_latencies) / len(evaluate_latencies):.3f}, "
        f"P95: {_percentile(evaluate_latencies, 0.95):.3f}"
    )
    print(
        f"Tokens LLM — llamadas: {client.total_calls}, prompt: {client.total_prompt_tokens}, "
        f"completion: {client.total_completion_tokens}, total: "
        f"{client.total_prompt_tokens + client.total_completion_tokens}"
    )

    summary = {
        "recall_at_5": recall_at_5,
        "mrr": mrr,
        "classification_accuracy": classification_accuracy,
        "search_latency_mean_s": sum(search_latencies) / len(search_latencies),
        "search_latency_p95_s": _percentile(search_latencies, 0.95),
        "evaluate_latency_mean_s": sum(evaluate_latencies) / len(evaluate_latencies),
        "evaluate_latency_p95_s": _percentile(evaluate_latencies, 0.95),
        "llm_calls": client.total_calls,
        "llm_prompt_tokens": client.total_prompt_tokens,
        "llm_completion_tokens": client.total_completion_tokens,
    }

    with (ROOT / "logs" / "eval_results.json").open("w", encoding="utf-8") as f:
        json.dump(
            {"content_results": content_results, "process_results": process_results, "summary": summary},
            f,
            indent=2,
            ensure_ascii=False,
        )
    print("\nResultados completos guardados en logs/eval_results.json")


if __name__ == "__main__":
    main()
