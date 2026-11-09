# TODO

Organizado por las 6 fases del curso (CC3103). Cada fase es un ciclo de trabajo.
Decisiones y gaps se registran en [DECISIONS.md](DECISIONS.md), no aquí.

## Fase 1 — Anteproyecto

- [x] Redactar secciones 1-11 del anteproyecto (ClaimTrace)
- [x] Estructurar el repositorio (`src/`, `data/`, `tests/`, `requirements.txt`)
- [ ] Limpiar typo en el resumen ejecutivo ("ClaimTrace jsjsjs")
- [ ] Completar secciones 12-16 del anteproyecto
  - [ ] Sección 12 — Evaluación: banco de pruebas (ver Fase 4) + tabla de métricas con metas
  - [ ] Sección 13 — Seguridad: controles para prompt injection, documentos no autorizados, info sensible, herramientas peligrosas, salidas inválidas, logs
  - [ ] Sección 14 — Riesgos: tabla riesgo/probabilidad/impacto/mitigación/prueba (mínimo 3-5 riesgos)
  - [ ] Sección 15 — Plan de Trabajo: tabla fase/actividad/responsable/entregable/fecha para las 6 fases
  - [ ] Sección 16 — Referencias: papers y herramientas citadas (Sentence Transformers, FAISS, BM25, LangGraph, etc.)
- [ ] Alinear el formato de salida (`answer`, `sources`, `abstained`, `tool_used`, `needs_human_review`) con las categorías `evidencia_suficiente/parcial/no_localizada`
- [ ] Completar el equipo a 3-4 integrantes (el curso lo exige, actualmente son 2)
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

- [ ] Construir banco de pruebas de 20 casos en `data/eval/` (campos: `id, question, expected_behavior, expected_sources, expected_pages, answerable, risk_level`)
  - [ ] 5 preguntas directas
  - [ ] 3 paráfrasis semántica
  - [ ] 3 con identificadores léxicos exactos
  - [ ] 3 compuestas (múltiples partes)
  - [ ] 2 ambiguas
  - [ ] 2 sin respuesta posible (abstención obligada)
  - [ ] 2 dependientes de versión/vigencia temporal
- [ ] Calcular métricas: Recall@k, MRR, fidelidad/fundamentación, precisión de citas, tasa de abstención, latencia (media y P95), consumo de tokens, costo estimado
- [ ] Comparar línea base vs. versión mejorada

## Fase 5 — Seguridad

- [ ] Diseñar casos adversarios: inyección de instrucciones, evasión de permisos, acciones críticas sin autorización, alucinación forzada
- [ ] Implementar validación de entradas, control de acceso a documentos, sanitización de logs
- [ ] Documentar cada prueba: amenaza, componente afectado, comportamiento esperado, resultado observado, mitigación

## Fase 6 — Demostración y Defensa

- [ ] Preparar guion de demo en vivo (15 min: 2 problema/usuario, 3 arquitectura, 4 demo, 3 métricas, 2 seguridad, 1 conclusiones)
- [ ] Escribir documento técnico (10-15 páginas)
- [ ] Preparar README y especificación de dependencias sin credenciales
- [ ] Preparar defensa oral individual
