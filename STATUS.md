# Estado actual del proyecto

Última actualización: 2026-11-10.

Foto del estado de Evidentia a hoy, para quien retome el proyecto desde aquí
(ej. Bianca, o Mónica en una sesión futura) sin tener que leer las 20+
entradas de `DECISIONS.md` primero. El detalle completo de *cómo* se llegó a
cada número y decisión está ahí — esto es solo el resumen.

## Completo y funcionando end-to-end

- **Fase 1 (Anteproyecto)**: redactado, secciones 1-16 completas. Quedan 2
  cosas cosméticas pendientes (ver `TODO.md`): reasignar tareas de
  "Integrante 3" entre Mónica y Bianca, y llenar fechas reales en la
  sección 15.
- **Fase 2 (Línea Base) y Fase 3 (Mejora Técnica)**: completas. Pipeline de
  ingesta, recuperación híbrida (semántica + BM25 propio + boost de
  identificadores), orquestador agéntico con LangGraph, y el esquema de
  salida obligatorio — todo implementado, probado con tests y contra el
  sistema real.
- **Fase 4 (Evaluación)**: el banco de 25 casos (`data/eval/test_cases.json`)
  ya corre contra el sistema completo (`scripts/run_eval.py`). Números
  actuales: **Recall@5 = 100% (21/21)**, **exactitud de clasificación =
  86.96% (20/23)**, verificado con un ablation de recuperación (no es un
  artefacto de corpus chico ni del boost de identificadores) y con el corpus
  duplicado a 20 documentos como distractores. 67/67 tests unitarios pasan.

## No empezado — esto es lo que sigue, no solo documentación

- **Fase 5 (Seguridad)**: los 7 casos adversarios (SEC01-SEC07) están
  *diseñados* en el anteproyecto pero *nada de los controles está
  implementado* (delimitación de contexto, detector de inyección, filtro por
  `owner_id`, lista blanca de dominios, límite de iteraciones, sanitizador de
  logs). Es la única fase de código que falta por completo.
- **Fase 6 (Demostración y Defensa)**: documento técnico final, guion de
  demo, preparación de la defensa oral — todo pendiente, pero puede apoyarse
  directamente en `DECISIONS.md` (ya tiene casi todo el contenido de
  "metodología" y "limitaciones" redactado).

## Pendientes menores dentro de Fase 4

No bloquean nada, ver `TODO.md` para el detalle:
- Recalibrar `expected_evidence_level` en algunos casos del banco
- Revisar la métrica Recall@5 para casos multi-documento (TC14)
- Aplicar los límites duros de `top_k`/`max_claims`
- Medir MRR/latencia/costo
- Comparar línea base vs. versión mejorada con el mismo banco

## Para retomar

- `TODO.md` tiene el checklist completo por fase (lo que falta son las
  casillas sin marcar `[ ]`).
- `DECISIONS.md` explica el *por qué* de cada decisión no obvia — vale la
  pena leerlo antes de tocar `evaluate_evidence.py`, `validate_citations.py`
  o la elección de modelo en LM Studio, porque varias cosas que parecen "se
  podría simplificar" ya se intentaron y fallaron por una razón documentada
  ahí (ej. por qué hay un `contradiction_check.py` separado, por qué el
  modelo es `qwen/qwen3.5-9b` y no uno más chico, por qué `version` se deriva
  del id de arXiv en vez de hardcodearse).
- `README.md` tiene el setup paso a paso (entorno conda, LM Studio, variables
  de entorno).
