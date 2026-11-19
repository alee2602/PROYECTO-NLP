"""Compara línea base (Fase 2: SemanticRetriever, solo semántico) vs.
versión mejorada (Fase 3: HybridRetriever, semántico+léxico+boost de
identificadores) con el MISMO banco de pruebas y el MISMO pipeline de
evaluate_claim (validate_citations/check_injection/check_contradiction se
mantienen activos en ambas variantes -- lo único que varía es el
retriever, para aislar el efecto real de la mejora de recuperación sobre
la clasificación final, no mezclarlo con mejoras posteriores del
evaluador).

Requiere LM Studio corriendo (ver README). Dobla el número de llamadas al
LLM respecto a scripts/run_eval.py (corre cada caso dos veces, una por
variante), así que tarda más.

Uso: venv\\Scripts\\python.exe scripts\\run_baseline_vs_improved.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.evaluate_evidence import evaluate_claim  # noqa: E402
from src.agent.llm_client import get_client  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.retrieval.retriever import SemanticRetriever  # noqa: E402
from src.schemas.chunk import ChunkMetadata  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOP_K = 5

# Misma excepción que scripts/run_eval.py: TC15 (categoría "ambigua") lista
# varias fuentes alternativas plausibles, no un conjunto obligatorio.
ANY_MATCH_CATEGORIES = {"ambigua"}

# Mismos casos que scripts/run_eval.py excluye de las métricas de
# contenido (pruebas de robustez de parámetros, no afirmaciones).
PROCESS_ONLY_CASES = {"TH03", "TH04"}


def load_chunks() -> list[ChunkMetadata]:
    chunks = []
    with (ROOT / "data" / "processed" / "chunks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            chunks.append(ChunkMetadata(**json.loads(line)))
    return chunks


def _recall_hit(category: str, expected: set[str], retrieved: set[str]) -> bool | None:
    if not expected:
        return None
    if len(expected) > 1 and category not in ANY_MATCH_CATEGORIES:
        return expected.issubset(retrieved)
    return bool(expected & retrieved)


def _mrr(ranked_doc_ids: list[str], expected: set[str]) -> float | None:
    if not expected:
        return None
    for rank, doc_id in enumerate(ranked_doc_ids, start=1):
        if doc_id in expected:
            return 1.0 / rank
    return 0.0


def run_variant(name: str, search_fn, cases: list[dict], client) -> list[dict]:
    rows = []
    for case in cases:
        ranked = search_fn(case["question"])
        ranked_doc_ids = [sc.chunk.document_id for sc in ranked]
        expected = set(case.get("expected_sources") or [])

        result = evaluate_claim(f"{case['id']}_{name}", case["question"], ranked, client=client)
        expected_level = case.get("expected_evidence_level")
        classification_match = (
            None if expected_level is None else result.evidence_level.value == expected_level
        )

        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "recall_hit": _recall_hit(case["category"], expected, set(ranked_doc_ids)),
                "mrr": _mrr(ranked_doc_ids, expected),
                "classification_match": classification_match,
                "actual_evidence_level": result.evidence_level.value,
                "expected_evidence_level": expected_level,
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    recall_cases = [r for r in rows if r["recall_hit"] is not None]
    mrr_cases = [r for r in rows if r["mrr"] is not None]
    classification_cases = [r for r in rows if r["classification_match"] is not None]
    return {
        "recall_at_5": sum(r["recall_hit"] for r in recall_cases) / len(recall_cases) if recall_cases else None,
        "mrr": sum(r["mrr"] for r in mrr_cases) / len(mrr_cases) if mrr_cases else None,
        "classification_accuracy": (
            sum(r["classification_match"] for r in classification_cases) / len(classification_cases)
            if classification_cases
            else None
        ),
        "n_cases": len(rows),
    }


def main():
    test_cases = json.loads((ROOT / "data" / "eval" / "test_cases.json").read_text(encoding="utf-8"))
    cases = [c for c in test_cases if c["id"] not in PROCESS_ONLY_CASES]
    chunks = load_chunks()

    baseline = SemanticRetriever()
    baseline.index_chunks(chunks)
    improved = HybridRetriever()
    improved.index_chunks(chunks)

    client = get_client()

    print(f"Corriendo {len(cases)} casos x 2 variantes (línea base, mejorada) contra LM Studio...\n")
    baseline_rows = run_variant("baseline", lambda q: baseline.search(q, top_k=TOP_K), cases, client)
    improved_rows = run_variant("improved", lambda q: improved.search(q, top_k=TOP_K), cases, client)

    baseline_summary = summarize(baseline_rows)
    improved_summary = summarize(improved_rows)

    print("=" * 90)
    print("RESUMEN: línea base (solo semántico) vs. mejorada (híbrido)")
    print("=" * 90)
    print(f"{'Métrica':<28} {'Línea base':>12} {'Mejorada':>12}")
    print("-" * 54)
    print(f"{'Recall@5':<28} {baseline_summary['recall_at_5']:>11.1%} {improved_summary['recall_at_5']:>11.1%}")
    print(f"{'MRR':<28} {baseline_summary['mrr']:>12.3f} {improved_summary['mrr']:>12.3f}")
    print(
        f"{'Exactitud clasificación':<28} "
        f"{baseline_summary['classification_accuracy']:>11.1%} {improved_summary['classification_accuracy']:>11.1%}"
    )

    print("\n--- Casos donde la clasificación cambia entre variantes ---")
    by_id_baseline = {r["id"]: r for r in baseline_rows}
    by_id_improved = {r["id"]: r for r in improved_rows}
    diffs = 0
    for case_id in by_id_baseline:
        b, i = by_id_baseline[case_id], by_id_improved[case_id]
        if b["actual_evidence_level"] != i["actual_evidence_level"]:
            diffs += 1
            print(
                f"  [{case_id}] línea_base={b['actual_evidence_level']} "
                f"mejorada={i['actual_evidence_level']} esperado={b['expected_evidence_level']}"
            )
    if diffs == 0:
        print("  (ninguno)")

    out = {
        "baseline": {"summary": baseline_summary, "rows": baseline_rows},
        "improved": {"summary": improved_summary, "rows": improved_rows},
    }
    out_path = ROOT / "logs" / "baseline_vs_improved.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultados completos guardados en {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
