"""Evidentia — interfaz Streamlit.

Uso: streamlit run app/streamlit_app.py
Requiere un servidor LLM compatible con OpenAI (LM Studio) — ver README.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app.helpers import (  # noqa: E402
    LEVEL_LABELS,
    document_text,
    ingest_upload,
    llm_status,
    load_corpus_chunks,
    load_corpus_documents,
    new_owner_id,
    result_rows,
    summary,
)
from src.agent.evaluate_evidence import evaluate_claim  # noqa: E402
from src.agent.orchestrator import DEFAULT_TOP_K, run_pipeline  # noqa: E402
from src.ingestion.pdf_loader import PDFValidationError  # noqa: E402
from src.limits import MAX_CLAIMS  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.schemas.output import EvidentiaOutput  # noqa: E402

st.set_page_config(page_title="Evidentia", page_icon="🔎", layout="wide")


@st.cache_resource(show_spinner="Indexando el corpus (solo la primera vez)...")
def get_retriever() -> HybridRetriever:
    retriever = HybridRetriever()
    retriever.index_chunks(load_corpus_chunks())
    return retriever


def chunk_lookup(retriever: HybridRetriever) -> dict:
    return {c.chunk_id: c for c in retriever._chunks}  # noqa: SLF001


def render_result(r: EvidentiaOutput, chunks: dict) -> None:
    label, kind = LEVEL_LABELS[r.evidence_level]
    getattr(st, kind)(f"**{label}**" + ("  ·  requiere revisión humana" if r.needs_human_review else ""))
    st.markdown(f"**Afirmación:** {r.claim}")
    st.markdown(f"**Análisis:** {r.answer}")
    if r.abstained:
        st.caption("El sistema se abstuvo: no encontró evidencia suficiente en el corpus.")
    for s in r.sources:
        chunk = chunks.get(s.chunk_id)
        with st.expander(f"📄 {s.source} — página {s.page} ({s.chunk_id})"):
            st.write(chunk.text if chunk else "(fragmento no disponible)")
    with st.expander("JSON de salida"):
        st.json(r.model_dump(mode="json"))


# --- estado de sesión ---
if "owner_id" not in st.session_state:
    st.session_state.owner_id = new_owner_id()
    st.session_state.uploaded = {}  # nombre -> document_id (ya indexados)
owner_id = st.session_state.owner_id

retriever = get_retriever()

# --- barra lateral ---
with st.sidebar:
    st.title("🔎 Evidentia")
    st.caption("Trazabilidad de evidencia en documentos académicos")
    ok, detail = llm_status()
    st.markdown(f"**LLM:** {'🟢 conectado' if ok else '🔴 sin conexión'}  \n`{detail}`")
    n_corpus = sum(1 for c in retriever._chunks if c.owner_id is None)  # noqa: SLF001
    st.markdown(f"**Corpus:** {n_corpus} fragmentos")
    if n_corpus == 0:
        st.warning("No hay corpus. Corre `python scripts/build_corpus.py`.")
    max_claims = st.slider("Máx. afirmaciones a analizar", 1, MAX_CLAIMS, 5)
    st.caption(f"Sesión: `{owner_id}` — tus PDFs solo se recuperan en esta sesión.")

if not ok:
    st.error(
        "No hay conexión con el LLM. Inicia el servidor de LM Studio y revisa "
        "`LLM_BASE_URL` / `LLM_MODEL` (ver README)."
    )

tab_doc, tab_claim = st.tabs(["Analizar documento", "Verificar una afirmación"])

# --- pestaña 1: documento completo ---
with tab_doc:
    source = st.radio("Fuente", ["Subir un PDF", "Documento del corpus"], horizontal=True)
    doc_id = None
    if source == "Subir un PDF":
        file = st.file_uploader("PDF académico (texto, no escaneado)", type=["pdf"])
        if file is not None:
            if file.name not in st.session_state.uploaded:
                try:
                    doc_id, new_chunks = ingest_upload(file.getvalue(), file.name, owner_id)
                except PDFValidationError as exc:
                    st.error(f"Archivo rechazado: {exc}")
                else:
                    retriever.index_chunks(new_chunks)
                    st.session_state.uploaded[file.name] = doc_id
                    st.success(f"Ingestado: {len(new_chunks)} fragmentos.")
            doc_id = st.session_state.uploaded.get(file.name)
    else:
        with_chunks = {c.document_id for c in retriever._chunks if c.owner_id is None}  # noqa: SLF001
        docs = [d for d in load_corpus_documents() if d["document_id"] in with_chunks]
        options = {f"{d['document_id']} — {d['title']}": d["document_id"] for d in docs}
        if options:
            doc_id = options[st.selectbox("Documento", list(options))]
            st.caption("Nota: el documento también está en el corpus, así que puede citarse a sí mismo.")
        else:
            st.info("No hay documentos de corpus disponibles.")

    if st.button("Analizar afirmaciones", type="primary", disabled=not (doc_id and ok)):
        text = document_text(retriever._chunks, doc_id)  # noqa: SLF001
        with st.spinner("Extrayendo y evaluando afirmaciones (puede tardar varios minutos)..."):
            st.session_state.results = run_pipeline(
                text, retriever, max_claims=max_claims, owner_id=owner_id
            )

    results = st.session_state.get("results")
    if results is not None:
        if not results:
            st.info("No se extrajeron afirmaciones verificables de este documento.")
        else:
            s = summary(results)
            c = st.columns(5)
            c[0].metric("Afirmaciones", s["total"])
            c[1].metric("Suficiente", s["suficiente"])
            c[2].metric("Parcial", s["parcial"])
            c[3].metric("No localizada", s["no_localizada"])
            c[4].metric("Revisión humana", s["revision"])
            st.dataframe(result_rows(results), width="stretch", hide_index=True)
            lookup = chunk_lookup(retriever)
            for r in results:
                with st.expander(f"{r.claim_id} — {LEVEL_LABELS[r.evidence_level][0]}"):
                    render_result(r, lookup)

# --- pestaña 2: una afirmación ---
with tab_claim:
    claim = st.text_area("Afirmación a verificar contra el corpus", height=100)
    if st.button("Verificar", disabled=not (claim.strip() and ok)):
        with st.spinner("Buscando evidencia y evaluando..."):
            evidence = retriever.search(claim, top_k=DEFAULT_TOP_K, owner_id=owner_id)
            result = evaluate_claim("CLAIM_000", claim.strip(), evidence)
        render_result(result, chunk_lookup(retriever))
