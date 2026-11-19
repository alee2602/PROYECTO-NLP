# Estado actual del proyecto

Última actualización: 2026-11-19.

Foto del estado de Evidentia a hoy, para quien retome el proyecto desde aquí
(ej. Bianca, o Mónica en una sesión futura) sin tener que leer las 30+
entradas de `DECISIONS.md` primero. El detalle completo de *cómo* se llegó a
cada número y decisión está ahí — esto es solo el resumen.

**Nota importante**: en algún momento entre el 11 y el 19 de noviembre, el
trabajo de Fase 4 de una sesión se perdió por no comitearse a tiempo (ver
`DECISIONS.md`, 2026-11-19). Se rehizo, pero es la razón por la que verás
"rehecho"/"re-verificado" en varias entradas recientes — **comitea seguido**.

## Completo y funcionando end-to-end

- **Fase 1 (Anteproyecto)**: redactado, secciones 1-16 completas. Nombres
  y fechas reales del plan de trabajo (tomadas de `git log`, no inventadas)
  y reasignación de tareas de "Integrante 3" en `PLAN_DE_TRABAJO.md`, listo
  para copiar a la sección 15.
- **Fase 2 (Línea Base) y Fase 3 (Mejora Técnica)**: completas. Pipeline de
  ingesta, recuperación híbrida (semántica + BM25 propio + boost de
  identificadores), orquestador agéntico con LangGraph, y el esquema de
  salida obligatorio — todo implementado, probado con tests y contra el
  sistema real.
- **Fase 4 (Evaluación)**: completa, incluyendo los 4 pendientes menores
  que quedaban. El banco de 25 casos (`data/eval/test_cases.json`) corre
  contra el sistema completo (`scripts/run_eval.py`). Números reales
  (corrida 2026-11-19, con la métrica de Recall@5 ya corregida para casos
  multi-documento): **Recall@5 = 95.24% (20/21)**, **MRR = 0.921**,
  **exactitud de clasificación = 91.30% (21/23)**. Los 2 casos que no
  coinciden (TC14, TC15) son limitaciones reales ya documentadas, no
  etiquetas mal calibradas — se revisó y se decidió NO tocar
  `test_cases.json`. **Comparación línea base (Fase 2) vs. mejorada
  (Fase 3)** con `scripts/run_baseline_vs_improved.py`: la mejora de
  recuperación sube la exactitud de clasificación final de 65.2% a 91.3%
  (+26 puntos) — evidencia concreta de que la mejora técnica importa.
  122/122 tests unitarios pasan. Bianca implementó y confirmó contra el
  sistema real los límites duros de `top_k≤20`/`max_claims≤15`
  (`src/limits.py`).
- **Fase 5 (Seguridad)**: completa. Los 7 controles SEC01-SEC07 están
  implementados, probados y confirmados con una corrida end-to-end real
  contra el sistema completo (`scripts/run_security_eval.py`) —
  **7/7 casos pasan**. Tabla de "Resultado observado" lista para copiar al
  anteproyecto en `DECISIONS.md`. Bianca agregó presupuestos de agente
  (tope de 3 iteraciones, 120 llamadas LLM, 10 llamadas externas por
  afirmación) y validación de DOI; corrigió un bug real en el filtro
  `owner_id` (se aplicaba después de recortar el pool de candidatos).
  **Decisión de equipo cerrada (2026-11-19)**: `owner_id=None` ahora oculta
  chunks privados de todos por defecto (antes no filtraba nada) — cero
  regresión en el corpus compartido actual. **Gap documentado, no oculto**:
  spaCy NER (para detectar nombres propios en logs, SEC07) sigue bloqueado
  por el Control de aplicaciones de Windows — la sanitización hoy es solo
  por regex (correos/teléfonos), ya confirmada contra el sistema real.
- **Interfaz** (`app/streamlit_app.py`, Bianca): subir un PDF, analizar sus
  afirmaciones o verificar una afirmación suelta — usa de verdad los
  controles de seguridad (SEC03, SEC06). Correr con
  `streamlit run app/streamlit_app.py`.

## No empezado

- **Fase 6 (Demostración y Defensa)**: `DOCUMENTO_TECNICO.md` y
  `GUION_DEMO.md` ya tienen un borrador completo con los números reales —
  falta revisarlos, ajustar estilo/extensión según lo que pida el curso, y
  preparar la defensa oral individual.

## Para retomar

- `TODO.md` tiene el checklist completo por fase (lo que falta son las
  casillas sin marcar `[ ]`).
- `PLAN_DE_TRABAJO.md` tiene la tabla de trabajo real (nombres, fechas,
  tareas no contempladas originalmente) para la sección 15 del anteproyecto.
- `DOCUMENTO_TECNICO.md` y `GUION_DEMO.md` son los borradores de Fase 6.
- `DECISIONS.md` explica el *por qué* de cada decisión no obvia — vale la
  pena leerlo antes de tocar `evaluate_evidence.py`, `validate_citations.py`,
  `hybrid.py` (filtro `owner_id`) o la elección de modelo en LM Studio,
  porque varias cosas que parecen "se podría simplificar" ya se intentaron
  y fallaron por una razón documentada ahí.
- `README.md` tiene el setup paso a paso (entorno conda, LM Studio —
  **ojo**: verificar siempre `lms ps` muestra `CONTEXT=16384` antes de
  correr una evaluación real; `lms load` sobre un modelo ya cargado no
  siempre aplica el flag de contexto nuevo, hay que `lms unload --all`
  primero si hay duda).
