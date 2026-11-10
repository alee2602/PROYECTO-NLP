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

- [ ] Armar corpus inicial
  - [ ] Elegir 5-10 documentos open access relacionados (vía OpenAlex/Crossref/arXiv)
  - [ ] Elegir documentos propios del equipo con autorización
  - [ ] Descargar y guardar en `data/raw/`
- [ ] Conseguir acceso al modelo generativo (API key de Claude/OpenAI/Gemini, o setup local con Ollama)
- [ ] Implementar pipeline de ingesta (`src/ingestion/`)
  - [ ] Carga y validación de PDF
  - [ ] Extracción de texto por página (PyMuPDF)
  - [ ] Limpieza/normalización de texto
  - [ ] Chunking (~450 tokens, solapamiento 80, respetando párrafos/secciones)
  - [ ] Asignación de metadatos por chunk (`chunk_id`, `document_id`, `page`, `section`, `source`, `version`, `doi`, `publication_year`)
- [ ] Generar embeddings (`src/retrieval/`) con `paraphrase-multilingual-MiniLM-L12-v2`
- [ ] Construir índice vectorial (FAISS)
- [ ] Recuperación semántica básica (sin híbrido todavía)
- [ ] Clasificación mínima de afirmaciones (suficiente/parcial/no localizada), sin flujo agéntico completo

## Fase 3 — Mejora Técnica

- [ ] Agregar búsqueda léxica BM25 + ponderación híbrida (70% semántica / 30% léxica)
- [ ] Agregar heurística de reranking
- [ ] Implementar orquestador agéntico (`src/agent/`, LangGraph) con tools:
  - [ ] `extract_claims`
  - [ ] `search_evidence`
  - [ ] `search_metadata`
  - [ ] `evaluate_evidence`
  - [ ] `validate_citations`
- [ ] Definir y validar esquema de salida con Pydantic (`src/schemas/`)

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
