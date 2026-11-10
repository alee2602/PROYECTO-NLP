# TODO

Organizado por las 6 fases del curso (CC3103). Cada fase es un ciclo de trabajo.
Decisiones y gaps se registran en [DECISIONS.md](DECISIONS.md), no aquí.

## Fase 1 — Anteproyecto

- [x] Redactar secciones 1-11 del anteproyecto
- [x] Estructurar el repositorio (`src/`, `data/`, `tests/`, `requirements.txt`)
- [x] Limpiar typo en el resumen ejecutivo y renombrar el proyecto a "Evidentia" en todo el documento
- [x] Completar secciones 12-16 del anteproyecto (Evaluación con 25 casos, Seguridad con 7 casos adversarios, Riesgos, Plan de Trabajo, Referencias)
- [x] Alinear el formato de salida (`answer`, `sources`, `abstained`, `tool_used`, `needs_human_review`) con `evidence_level` como extensión del esquema
- [x] **Decisión de equipo**: se queda en 2 integrantes (Mónica, Bianca) — decisión final.
- [ ] Reasignar en la sección 15 (Plan de Trabajo) las tareas que estaban asignadas a "Integrante 3" (interfaz en Fase 3, evaluación en Fase 4) entre Mónica y Bianca — pendiente, se hace más adelante
- [ ] Llenar fechas concretas en la sección 15 (actualmente placeholders `[fecha]`)
- [ ] Entregar anteproyecto

## Fase 2 — Línea Base

- [x] Armar corpus inicial: 10 papers de arXiv (D01-D10) vía `scripts/build_corpus.py`, descargados a `data/raw/` (no versionados) y procesados a `data/processed/documents.json` (metadata, sí versionado) y `chunks.jsonl` (texto completo, no versionado — ver DECISIONS.md)
- [ ] Elegir documentos propios del equipo con autorización (opcional, el corpus de arXiv ya cumple el mínimo de 5-10)
- [ ] Conseguir acceso al modelo generativo (API key de Claude/OpenAI/Gemini, o setup local con Ollama)
- [x] Implementar pipeline de ingesta (`src/ingestion/`)
  - [x] Carga y validación de PDF (`pdf_loader.py`: tipo, tamaño, páginas, cifrado)
  - [x] Extracción de texto por página (`extractor.py`, PyMuPDF)
  - [x] Limpieza de texto y remoción de encabezados/pies repetidos (`cleaner.py`)
  - [x] Chunking (`chunker.py`): ventana deslizante de ~450 palabras, solapamiento 80 (aproximación por palabra, no tokenizer real — ver nota en el código)
  - [x] Metadatos por documento y por chunk con Pydantic (`src/schemas/document.py`, `src/schemas/chunk.py`), orquestado en `pipeline.py`
  - [x] Pruebas unitarias (`tests/test_ingestion.py`, 10 casos, todos pasando)
- [x] Generar embeddings (`src/retrieval/embeddings.py`) con `paraphrase-multilingual-MiniLM-L12-v2`
- [x] Construir índice vectorial (`src/retrieval/index.py`, FAISS `IndexFlatIP`)
- [x] Recuperación semántica básica (`src/retrieval/retriever.py`, `SemanticRetriever`, sin híbrido todavía) — probado end-to-end con el modelo real en `tests/test_retriever.py`
- [x] Clasificación mínima de afirmaciones (`src/agent/evaluate_evidence.py`), sin flujo agéntico completo todavía — usa `src/agent/llm_client.py`, compatible con LM Studio local o cualquier API compatible con OpenAI vía variables de entorno (`.env.example`)
- [x] Probar `evaluate_claim` contra LM Studio real (`qwen2.5-vl-7b-instruct`) — funciona con salida estructurada vía JSON Schema (ver `scripts/check_llm.py`)

## Fase 3 — Mejora Técnica

- [x] **Hallazgos de `scripts/demo.py` contra datos reales — resueltos (ver DECISIONS.md)**:
  - [x] Búsqueda léxica BM25 implementada desde cero en `src/retrieval/lexical.py` (sin dependencia externa) + `HybridRetriever` en `src/retrieval/hybrid.py` (70/30 semántica/léxica + boost de identificadores técnicos exactos tipo "BM25"/"RAGAS")
  - [x] Filtro de stopwords español/inglés en el tokenizador léxico (la consulta está en español, el corpus en inglés — sin esto, palabras funcionales generaban coincidencias falsas)
  - [x] Subido `top_k` de 3 a 5 en la demo (como pedía el anteproyecto)
  - [x] Normalización de ligaduras tipográficas (ﬁ, ﬂ, etc.) en `src/ingestion/cleaner.py` — artefacto común de PDFs académicos
  - [x] Diagnosticado y resuelto el error "context length exceeded" (el modelo en LM Studio estaba cargado con 4096 tokens de contexto; con 5 chunks no alcanzaba — hay que cargarlo con `lms load <modelo> --context-length 16384` o más, ver README)
- [x] **Falso positivo de contradicción — mejorado, no 100% perfecto**: se agregó regla explícita + ejemplo few-shot en `SYSTEM_PROMPT` (`src/agent/evaluate_evidence.py`) para que evidencia que contradice la afirmación no se clasifique como `evidencia_suficiente`. Resultado real: el caso de prueba (afirmación "imposible detectar" vs. paper de detección) ya no da falso positivo — ahora sale `evidencia_no_localizada` (abstención). Lo ideal sería `evidencia_parcial` explicando la contradicción explícitamente, que el modelo (7B local) no siempre logra, pero el riesgo principal (afirmar respaldo falso) ya no ocurre. Revisar con un modelo más grande o con más casos del banco de pruebas real en Fase 4.
- [x] `answer` nunca queda vacío: agregado `minLength: 1` en `RESPONSE_SCHEMA`, no solo instrucción de prompt
- [ ] (Informativo, no requiere acción) a veces LM Studio/llama.cpp crashea generando JSON con grammar ("Unexpected empty grammar stack...") — es un bug conocido del motor, no nuestro; el sistema ya se abstiene con `needs_human_review=True` tras el reintento, que es el comportamiento correcto por diseño (anteproyecto sección 11)
- [x] **Probado con afirmaciones nuevas (`scripts/demo_fresh.py`, documentos D02/D05/D06/D10 no usados antes) para medir generalización real, no solo el caso ya calibrado** — encontró un bug nuevo: el LLM validaba una cifra inventada ("45% de mejora") como `evidencia_suficiente` citando un chunk que ni la menciona
- [x] **`validate_citations` implementado como código determinístico** (`src/agent/validate_citations.py`), no delegado al LLM: (1) rechaza citas a chunks que no fueron recuperados, (2) si la afirmación tiene una cifra específica, verifica que aparezca literalmente en el texto citado, si no degrada `evidencia_suficiente` → `evidencia_parcial` + `needs_human_review=true`. 5 pruebas deterministas en `tests/test_validate_citations.py`, no dependen de un LLM real.
- [x] **Migrado de `venv` a entorno conda** (`conda activate evidentia`) — Smart App Control bloqueaba el `torch` instalado por pip; el de Anaconda no tiene ese problema (ver DECISIONS.md). Setup actualizado en README.
- [x] Heurística de reranking: ya satisfecha por la combinación de puntajes semántico+léxico en `HybridRetriever` (es literalmente lo que pide el anteproyecto sección 10 como "heurística inicial"); un modelo de reranking dedicado queda como mejora futura opcional
- [ ] Implementar orquestador agéntico (`src/agent/`, LangGraph) que conecte las tools ya implementadas en un solo flujo:
  - [ ] `extract_claims` — pendiente, todavía no implementado
  - [x] `search_evidence` — ya existe como `HybridRetriever.search` (`src/retrieval/hybrid.py`)
  - [x] `search_metadata` — implementado (`src/agent/search_metadata.py`, consulta Crossref, degrada a `None` si falla la red; probado con mocks y contra la API real)
  - [x] `evaluate_evidence` (ya implementado como función independiente; falta integrarlo al grafo de LangGraph)
  - [x] `validate_citations` (ya implementado y conectado dentro de `evaluate_claim`; falta exponerlo como tool independiente del agente si el diseño de LangGraph lo requiere)
- [ ] Definir y validar esquema de salida con Pydantic (`src/schemas/`) — ya existe `EvidentiaOutput`, falta confirmar que encaja sin cambios dentro del flujo de LangGraph

## Fase 4 — Evaluación

- [x] Diseñar el banco de pruebas (25 casos: TC01-TC20 + TH01-TH05) en el anteproyecto, sección 12
- [ ] Pasar el banco de pruebas de la tabla del anteproyecto a `data/eval/test_cases.json` (campos: `id, question, expected_behavior, expected_sources, expected_pages, answerable, risk_level`)
- [ ] Fijar documentos y páginas reales del corpus D01-D10 (hoy son "por fijar" en el anteproyecto) una vez cerrado el corpus en Fase 2
- [ ] Calcular métricas: Recall@5, MRR, fidelidad/fundamentación, exactitud de clasificación, cobertura fáctica, precisión de citas, tasa de abstención, latencia (media y P95), tokens/invocaciones/costo
- [ ] Comparar línea base (Fase 2) vs. versión mejorada (Fase 3) con el mismo banco

## Fase 5 — Seguridad

- [x] Diseñar casos adversarios (SEC01-SEC07, anteproyecto sección 13): inyección directa/indirecta, evasión de permisos, acción crítica sin autorización, alucinación forzada, archivo malicioso, fuga de datos en logs
- [ ] Implementar los controles descritos: delimitación de contexto, detector de patrones de inyección, filtro por `owner_id`, lista blanca de dominios externos, límite de iteraciones/llamadas, validación Pydantic + `validate_citations`, sanitizador de logs (regex + spaCy NER)
- [ ] Ejecutar SEC01-SEC07 contra el sistema real y llenar la columna "Resultado observado" (hoy "Por medir") en el anteproyecto

## Fase 6 — Demostración y Defensa

- [ ] Preparar guion de demo en vivo (15 min: 2 problema/usuario, 3 arquitectura, 4 demo, 3 métricas, 2 seguridad, 1 conclusiones)
- [ ] Escribir documento técnico (10-15 páginas)
- [ ] Preparar README y especificación de dependencias sin credenciales
- [ ] Preparar defensa oral individual
