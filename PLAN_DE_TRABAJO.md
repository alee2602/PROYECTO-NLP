# Plan de trabajo real (para la sección 15 del anteproyecto)

El anteproyecto original dejó la sección 15 con fechas placeholder (`[fecha]`)
y tareas asignadas a un "Integrante 3" hipotético que nunca se unió al
equipo (decisión de equipo: quedarse en 2 integrantes, ver `DECISIONS.md`).
Esta tabla reemplaza esos placeholders con lo que realmente pasó —
responsable y fecha real, tomados de `git log`, no inventados — para
copiar directo a la sección 15.

## Tabla de trabajo por fase

| Fase | Tarea | Responsable | Fecha |
|---|---|---|---|
| 1 — Anteproyecto | Estructura del repo, renombrar a Evidentia, marcar Fase 1 completa | Mónica | 2026-11-04 a 2026-11-09 |
| 2 — Línea Base | Pipeline de ingesta (PDF→texto→limpieza→chunking), esquemas Pydantic | Mónica | 2026-11-09 |
| 2 — Línea Base | Recuperación semántica (FAISS), cliente LLM (REST directo, sin SDK de OpenAI) | Mónica | 2026-11-09 |
| 2 — Línea Base | Corpus inicial (10 papers de arXiv) y validación de la recuperación | Mónica | 2026-11-09 |
| 3 — Mejora Técnica | Recuperación híbrida (BM25 propio + boost de identificadores), limpieza cross-lingüe | Mónica | 2026-11-10 |
| 3 — Mejora Técnica | `validate_citations` determinístico, migración a entorno conda | Mónica | 2026-11-10 |
| 3 — Mejora Técnica | `extract_claims` + orquestador agéntico (LangGraph), filtro de vaguedad | Mónica | 2026-11-10 |
| 4 — Evaluación | Banco de 25 casos + runner (`run_eval.py`), primera corrida real | Mónica | 2026-11-10 |
| 4 — Evaluación | Ablation de recuperación (corpus duplicado, verificación de Recall@5) | Mónica | 2026-11-10 |
| 4 — Evaluación | Cambio de modelo (`qwen/qwen3.5-9b`) y arreglos de clasificación (arXiv-ID, metadata de versión) | Mónica | 2026-11-10 |
| 4 — Evaluación | Límites duros de parámetros (`top_k≤20`, `max_claims≤15`) | Bianca | 2026-11-10 |
| 4 — Evaluación | Confirmación de TH03 contra el sistema real | Mónica | 2026-11-11 |
| 4 — Evaluación | Métrica de Recall@5 corregida para afirmaciones compuestas, MRR, latencia/tokens, comparación línea base vs. mejorada | Mónica | 2026-11-19 |
| 5 — Seguridad | Implementación y verificación de SEC01-SEC07 (los 7 controles) | Mónica | 2026-11-11 |
| 5 — Seguridad | Presupuestos de agente (iteraciones, llamadas LLM, llamadas externas), validación de DOI | Bianca | 2026-11-14 |
| 5 — Seguridad | Corrección del filtro `owner_id` (se aplicaba después de recortar el pool de candidatos) | Bianca | 2026-11-14 |
| 5 — Seguridad | Decisión de equipo: `owner_id=None` debe ocultar chunks privados por defecto (antes no filtraba nada) | Mónica | 2026-11-19 |
| 6 — Demostración | Documento técnico, guion de demo, plan de trabajo actualizado | Mónica | 2026-11-19 |

## Tareas no contempladas en el plan original

El anteproyecto no las anticipó explícitamente como tareas propias, pero
resultaron necesarias y se hicieron:

- **Interfaz Streamlit** (`app/streamlit_app.py`): el anteproyecto asignaba
  "interfaz" genéricamente a Fase 3 / Integrante 3. En la práctica se
  construyó después, en paralelo a Fase 5 (Bianca, 2026-11-16) — permite
  subir un PDF, analizar sus afirmaciones o verificar una afirmación suelta,
  y usa de verdad los controles de seguridad ya implementados (`owner_id`
  de sesión para SEC03, validación de archivo para SEC06).
- **Migración de entorno** (`venv` → `conda`): no estaba en el plan; fue
  necesaria porque Windows Smart App Control bloqueaba binarios nativos
  instalados por `pip` (`torch`, el SDK de `openai`) — ver `DECISIONS.md`.
- **Reconciliación de dos implementaciones paralelas de Fase 5**: Mónica y
  Bianca implementaron seguridad por separado sin coordinarse primero; se
  resolvió conservando la de Mónica (ya verificada) y portando las piezas
  adicionales de Bianca (presupuestos, validación de DOI, corrección del
  filtro `owner_id`). Lección para las fases que quedan: coordinar quién
  toca qué módulo antes de empezar, no después.
- **Hallazgo y corrección de 2 bugs preexistentes** no relacionados con la
  tarea que se estaba haciendo en el momento: `pdf_loader.py` cerraba el
  documento antes de leer `doc.page_count` en el mensaje de error (apareció
  al escribir tests reales para SEC06); y un `PermissionError` de Windows al
  limpiar un directorio temporal después de que `fitz` fallara al abrir un
  PDF inválido (apareció al correr los tests después del `git pull` de los
  cambios de Bianca).

## Reasignación de tareas de "Integrante 3"

El anteproyecto original (sección 15) asignaba a un tercer integrante
hipotético: interfaz (Fase 3) y evaluación (Fase 4). Con el equipo
confirmado en 2 personas, esto quedó así en la práctica (no por asignación
previa, sino por cómo se repartió el trabajo real):

- **Evaluación (Fase 4)**: Mónica — banco de pruebas, runner, métricas,
  ablation, comparación línea base vs. mejorada.
- **Interfaz**: Bianca — Streamlit UI, construida en Fase 5 en vez de
  Fase 3 (se priorizó tener el pipeline agéntico y la seguridad sólidos
  antes de exponerlos en una interfaz).
