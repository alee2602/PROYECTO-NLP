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
- [x] **Orquestador agéntico implementado con LangGraph** (`src/agent/orchestrator.py`): grafo `extract → search → evaluate → (refinar búsqueda una vez si no hay evidencia) → finalize`, iterando sobre todas las afirmaciones extraídas de un documento. 4 pruebas deterministas (`tests/test_orchestrator.py`) + probado end-to-end contra un documento real (D04) con LM Studio real.
  - [x] `extract_claims` — implementado (`src/agent/extract_claims.py`) + filtro determinístico de afirmaciones vagas (`_is_too_vague`, ver DECISIONS.md — las instrucciones de prompt solas no bastaron)
  - [x] `search_evidence` — ya existe como `HybridRetriever.search` (`src/retrieval/hybrid.py`)
  - [x] `search_metadata` — implementado (`src/agent/search_metadata.py`, consulta Crossref, degrada a `None` si falla la red; probado con mocks y contra la API real)
  - [x] `evaluate_evidence` — implementado e integrado al grafo
  - [x] `validate_citations` — implementado y conectado dentro de `evaluate_claim`, atrapó una cita alucinada real en la prueba end-to-end contra D04
- [x] Esquema de salida Pydantic (`EvidentiaOutput`) — confirmado que encaja sin cambios dentro del flujo de LangGraph (el orquestador devuelve `list[EvidentiaOutput]` directamente)
- [ ] **Pendiente real, no cosmético**: CLAIM_002 en la prueba de D04 todavía cita un documento parcialmente no relacionado junto con el correcto (mitigado por terminar en `evidencia_parcial` + revisión humana, no resuelto de raíz). El filtro de vaguedad es una heurística angosta — revisar con más documentos/afirmaciones si aparecen más casos así.

## Fase 4 — Evaluación

- [x] Diseñar el banco de pruebas (25 casos: TC01-TC20 + TH01-TH05) en el anteproyecto, sección 12
- [x] **Banco de pruebas pasado a `data/eval/test_cases.json`** con afirmaciones reales (no genéricas) basadas en contenido verificado de D01-D10, páginas confirmadas
- [x] **Runner implementado y corrido (`scripts/run_eval.py`)** contra el sistema completo (recuperación + LLM real + validate_citations). Resultado guardado en `logs/eval_results.json` (no versionado, reproducible).
  - Primera corrida (modelo `qwen2.5-vl-7b-instruct`, corpus 10 docs): Recall@5=100%, clasificación=30% (7/23)
- [x] **Verificado que el Recall@5=100% no es un artefacto**: ablation de recuperación (`scripts/run_retrieval_ablation.py`) + corpus ampliado a 20 documentos con distractores reales (`scripts/add_corpus_documents.py`, D11-D20). El 100% se sostiene igual con el doble de documentos; el boost de identificadores solo rescata 1 caso específico (no está "cargando" el resultado). Ver DECISIONS.md para la tabla completa.
- [x] **Contradicción (TC08) resuelta cambiando de modelo, no con más prompt engineering**: se probó `qwen/qwen3.5-9b` (texto puro, razonamiento) en vez de `qwen2.5-vl-7b-instruct` (visión-lenguaje). Se encontró y arregló un bug de compatibilidad en el camino (`reasoning_content` vs `content`, ver DECISIONS.md, ahora arreglado en `src/agent/llm_client.py` de forma genérica para cualquier modelo "thinking").
- [x] **Segunda corrida completa con el modelo nuevo** (corpus de 20 docs, más difícil): Recall@5=100% (21/21), **clasificación=69.57% (16/23)** — más del doble, sin fallas de generación y sin falsos positivos peligrosos; los 7 casos restantes son todos calibración conservadora (segura), no errores de razonamiento.
- [x] **Clasificación mejorada a 86.96% (20/23)** con dos causas raíz arregladas de verdad (no prompt tuning): (1) `validate_citations` tomaba IDs de arXiv como cifras factuales a verificar — arreglado excluyéndolos antes de extraer números; (2) bug real de datos: `version` estaba hardcodeado en "1" para los 20 documentos del corpus pese a que `source` sí tenía el sufijo correcto — arreglado en `src/ingestion/arxiv_source.py` (`extract_version()`) y parcheados los datos existentes. Un tercer intento (endurecer la regla de "hechos compuestos" en el prompt) causó una regresión neta (dos casos que antes pasaban empezaron a fallar) y se revirtió. Se confirmó no-determinismo residual del motor local en casos límite (mismo código, dos corridas, conjuntos de fallos distintos). Ver DECISIONS.md para el detalle completo.
- [ ] Recalibrar `expected_evidence_level` en varios casos del banco (algunos esperaban "suficiente" donde "parcial" es defendible — ver DECISIONS.md)
- [ ] TC14: posible gap de metodología propia, no del sistema — Recall@5 usa overlap "any" contra `expected_sources`, por lo que un caso compuesto (dos documentos esperados) puede marcar `recall_hit=True` con solo uno de los dos recuperado. Revisar si conviene una métrica "all" para casos multi-documento.
- [ ] Implementar límites duros de parámetros (`top_k≤20`, `max_claims≤15`, anteproyecto sección 11) — TH03 confirmó que hoy NO se aplican
- [ ] Calcular métricas adicionales: MRR, cobertura fáctica, latencia (media/P95), tokens/invocaciones/costo
- [ ] Comparar línea base (Fase 2, solo semántico) vs. versión mejorada (Fase 3, híbrido) con el mismo banco — hoy solo se corrió contra la versión mejorada

## Fase 5 — Seguridad

- [x] Diseñar casos adversarios (SEC01-SEC07, anteproyecto sección 13): inyección directa/indirecta, evasión de permisos, acción crítica sin autorización, alucinación forzada, archivo malicioso, fuga de datos en logs
- [ ] Implementar los controles descritos: delimitación de contexto, detector de patrones de inyección, filtro por `owner_id`, lista blanca de dominios externos, límite de iteraciones/llamadas, validación Pydantic + `validate_citations`, sanitizador de logs (regex + spaCy NER)
- [ ] Ejecutar SEC01-SEC07 contra el sistema real y llenar la columna "Resultado observado" (hoy "Por medir") en el anteproyecto

## Fase 6 — Demostración y Defensa

- [ ] Preparar guion de demo en vivo (15 min: 2 problema/usuario, 3 arquitectura, 4 demo, 3 métricas, 2 seguridad, 1 conclusiones)
- [ ] Escribir documento técnico (10-15 páginas)
- [ ] Preparar README y especificación de dependencias sin credenciales
- [ ] Preparar defensa oral individual
