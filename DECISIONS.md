# Decisions log

Registro de decisiones de diseño, iteraciones y gaps abiertos del proyecto.
Sirve como base para las secciones de "limitaciones" y "trabajo futuro" del
documento técnico final. Cada entrada nueva va arriba (más reciente primero).

Formato por entrada:

```
## [Fecha] Título corto de la decisión

**Contexto**: por qué se necesitaba decidir esto.
**Decisión**: qué se decidió.
**Alternativas consideradas**: qué más se evaluó y por qué no se eligió.
**Estado**: propuesta / confirmada / revertida.
**Gaps abiertos**: qué queda pendiente o sin resolver por esta decisión.
```

---

## [2026-11-09] Estructura inicial del repositorio

**Contexto**: había que empezar a trabajar en paralelo a completar el anteproyecto, sin esperar a tener el equipo completo.
**Decisión**: carpetas `data/{raw,processed,eval}`, `src/{ingestion,retrieval,agent,schemas}`, `tests/`, `docs/`. Material del curso y corpus (`*.pdf`, `*.docx`, `*.pptx`) excluidos de git vía `.gitignore`.
**Alternativas consideradas**: ninguna, es la estructura estándar para un proyecto de este tipo.
**Estado**: confirmada.
**Gaps abiertos**: ninguno.

## [2026-11-09] Dominio del proyecto: trazabilidad de evidencia en documentos académicos

**Contexto**: el curso permite tema libre si hay acceso legal a fuentes y el resultado es evaluable; se evaluaron varias opciones (D&D SRD, mitología maya, wikis de videojuegos, reglamento UVG, documentación técnica, etc.) antes de decidir.
**Decisión**: ClaimTrace — sistema que verifica si afirmaciones en documentos académicos tienen respaldo documental, usando NLP + RAG + flujo agéntico. Cae dentro del dominio sugerido "Literatura Científica" pero con un ángulo propio (verificación de evidencia, no solo búsqueda).
**Alternativas consideradas**: dominios más nicho (juegos, mitología) descartados por riesgo de parecer poco serios en la defensa; dominios genéricos de soporte técnico descartados por ser menos originales.
**Estado**: confirmada.
**Gaps abiertos**: equipo actual es de 2 personas, el curso exige 3-4 — pendiente de resolver antes de poder entregar.

## [2026-11-09] Stack tecnológico inicial

**Contexto**: definir herramientas concretas para implementar el pipeline de ingesta, recuperación y generación.
**Decisión**: Python + Streamlit (interfaz) + PyMuPDF (PDF) + spaCy/Sentence Transformers (NLP) + `paraphrase-multilingual-MiniLM-L12-v2` (embeddings, 384 dim, multilingüe/español) + FAISS (índice vectorial) + BM25 (búsqueda léxica) + LangGraph (orquestación agéntica) + Pydantic (validación de esquema).
**Alternativas consideradas**: Chroma como alternativa a FAISS si el manejo de metadatos resulta más conveniente durante el desarrollo.
**Estado**: propuesta — sujeta a validación de compatibilidad/rendimiento durante la Fase 2.
**Gaps abiertos**: falta elegir y configurar el modelo generativo (LLM) para la generación fundamentada — ver TODO Fase 2.

## [2026-11-09] Estrategia de chunking y recuperación

**Contexto**: definir cómo segmentar documentos y recuperar evidencia relevante por afirmación.
**Decisión**: chunks de ~450 tokens con solapamiento de 80, respetando límites de párrafo/sección. Búsqueda híbrida: 70% semántica + 30% BM25 (ajustable según resultados del banco de pruebas). top_k=5 inicial. Reranking inicial por heurística de combinación de puntajes.
**Alternativas consideradas**: modelo de reranking dedicado — pospuesto como mejora futura si el rendimiento inicial no alcanza las metas.
**Estado**: propuesta — sujeta a ajuste en Fase 3 con datos reales del banco de pruebas.
**Gaps abiertos**: pesos de la búsqueda híbrida (70/30) no están validados empíricamente todavía.

## [2026-11-09] Formato de salida — gap identificado

**Contexto**: el curso exige que toda respuesta del sistema siga un esquema fijo (`answer`, `sources[]`, `abstained`, `tool_used`, `needs_human_review`), pero el anteproyecto actual define la salida como clasificación en 3 categorías (`evidencia_suficiente/parcial/no_localizada`) sin mapear explícitamente a ese esquema.
**Decisión**: pendiente — hay que definir cómo mapear la clasificación de 3 categorías al esquema obligatorio antes de implementar `src/schemas/`.
**Alternativas consideradas**: n/a, todavía no resuelto.
**Estado**: propuesta.
**Gaps abiertos**: diseño del mapeo clasificación → esquema de salida. Ver TODO Fase 1.
