from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.retrieval.hybrid import HybridRetriever
from src.retrieval.index import ScoredChunk
from src.schemas.output import EvidenceLevel, EvidentiaOutput

from .evaluate_evidence import evaluate_claim
from .extract_claims import extract_claims as extract_claims_tool
from .llm_client import LLMClient, get_client

# anteproyecto sección 10: top_k=5 inicial; si no hay evidencia, el flujo de
# decisión agéntico puede ampliar la búsqueda antes de abstenerse.
DEFAULT_TOP_K = 5
REFINED_TOP_K = 10


class GraphState(TypedDict):
    document_text: str
    max_claims: int
    claims: list[str]
    claim_index: int
    results: list[EvidentiaOutput]
    current_evidence: list[ScoredChunk]
    current_result: EvidentiaOutput | None
    refined: bool
    retriever: HybridRetriever
    client: LLMClient


def _node_extract(state: GraphState) -> dict:
    claims = extract_claims_tool(
        state["document_text"], max_claims=state["max_claims"], client=state["client"]
    )
    return {"claims": claims, "claim_index": 0, "results": []}


def _node_search(state: GraphState) -> dict:
    claim = state["claims"][state["claim_index"]]
    top_k = REFINED_TOP_K if state.get("refined") else DEFAULT_TOP_K
    evidence = state["retriever"].search(claim, top_k=top_k)
    return {"current_evidence": evidence}


def _node_evaluate(state: GraphState) -> dict:
    idx = state["claim_index"]
    claim = state["claims"][idx]
    result = evaluate_claim(
        f"CLAIM_{idx:03d}", claim, state["current_evidence"], client=state["client"]
    )
    return {"current_result": result}


def _should_refine(state: GraphState) -> str:
    result = state["current_result"]
    if result.evidence_level == EvidenceLevel.NO_LOCALIZADA and not state.get("refined"):
        return "refine"
    return "finalize"


def _node_mark_refined(state: GraphState) -> dict:
    return {"refined": True}


def _node_finalize_claim(state: GraphState) -> dict:
    results = state["results"] + [state["current_result"]]
    return {"results": results, "claim_index": state["claim_index"] + 1, "refined": False}


def _has_more_claims(state: GraphState) -> str:
    return "search" if state["claim_index"] < len(state["claims"]) else "end"


def build_graph():
    """Flujo de decisión agéntico (anteproyecto sección 11): extrae
    afirmaciones, recupera evidencia para cada una, evalúa (evaluate_claim ya
    aplica validate_citations internamente), y si no encuentra evidencia
    reintenta UNA vez con una búsqueda más amplia antes de abstenerse."""
    graph = StateGraph(GraphState)
    graph.add_node("extract", _node_extract)
    graph.add_node("search", _node_search)
    graph.add_node("evaluate", _node_evaluate)
    graph.add_node("mark_refined", _node_mark_refined)
    graph.add_node("finalize_claim", _node_finalize_claim)

    graph.set_entry_point("extract")
    graph.add_conditional_edges("extract", _has_more_claims, {"search": "search", "end": END})
    graph.add_edge("search", "evaluate")
    graph.add_conditional_edges(
        "evaluate", _should_refine, {"refine": "mark_refined", "finalize": "finalize_claim"}
    )
    graph.add_edge("mark_refined", "search")
    graph.add_conditional_edges(
        "finalize_claim", _has_more_claims, {"search": "search", "end": END}
    )

    return graph.compile()


def run_pipeline(
    document_text: str,
    retriever: HybridRetriever,
    max_claims: int = 10,
    client: LLMClient | None = None,
) -> list[EvidentiaOutput]:
    client = client or get_client()
    app = build_graph()
    initial_state: GraphState = {
        "document_text": document_text,
        "max_claims": max_claims,
        "claims": [],
        "claim_index": 0,
        "results": [],
        "current_evidence": [],
        "current_result": None,
        "refined": False,
        "retriever": retriever,
        "client": client,
    }
    final_state = app.invoke(initial_state)
    return final_state["results"]
