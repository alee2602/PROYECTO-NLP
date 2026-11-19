# Guion de demo — Evidentia (15 minutos)

Estructura pedida por el curso: 2 min problema/usuario, 3 min arquitectura,
4 min demo en vivo, 3 min métricas, 2 min seguridad, 1 min conclusiones.

**Antes de empezar** (checklist, no durante los 15 minutos):
- [ ] LM Studio corriendo, modelo `qwen/qwen3.5-9b` cargado **con
  `--context-length 16384`** (el contexto por defecto, 4096, hace fallar
  casi todas las evaluaciones silenciosamente — verificar con
  `lms ps` antes de empezar, no asumir).
- [ ] Corpus construido (`data/processed/chunks.jsonl` existe).
- [ ] `streamlit run app/streamlit_app.py` abierto y probado una vez antes
  de la presentación (la primera indexación tarda unos segundos).
- [ ] Tener a mano un PDF corto de prueba para la subida en vivo (algo que
  NO esté ya en el corpus, para que se note la diferencia).

---

## 1. Problema y usuario (2 min)

- Verificar a mano si una afirmación de un documento académico está
  realmente respaldada por su fuente es lento y propenso a error —
  sobre todo con decenas de referencias y sin tiempo de releer cada una.
- Usuario objetivo: alguien que revisa un documento académico (estudiante,
  investigador, revisor) y quiere saber, afirmación por afirmación, si el
  corpus disponible la respalda, la contradice, o no dice nada al respecto.
- La promesa del sistema no es "confiar en el LLM" — es que cada
  respuesta venga acompañada de la cita exacta (documento, página, chunk)
  para que la persona pueda verificarla ella misma en segundos, y que el
  sistema se abstenga en vez de inventar cuando no hay evidencia real.

## 2. Arquitectura (3 min)

Mostrar el diagrama de `DOCUMENTO_TECNICO.md` sección 3 (o dibujarlo en
vivo): extract_claims → HybridRetriever → evaluate_claim (LLM + 3 vetos
determinísticos) → EvidentiaOutput.

Punto central a explicar, no solo mostrar: **el LLM no es la última
palabra**. Después de que el modelo clasifica, código determinístico
verifica: ¿la cita existe de verdad entre lo recuperado? ¿las cifras que
menciona la afirmación aparecen literalmente en el texto citado? ¿hay un
patrón de manipulación en la afirmación o en el documento? Si algo de esto
falla, el sistema degrada la clasificación o se abstiene — no importa qué
tan convencido "suene" el LLM.

Mencionar brevemente: recuperación híbrida (semántica + léxica) porque las
consultas están en español y el corpus en inglés — lo semántico solo
pierde términos técnicos exactos como "BM25" o "RAGAS".

## 3. Demo en vivo (4 min)

Dos flujos cortos en la interfaz Streamlit:

1. **Verificar una afirmación suelta** (pestaña "Verificar una
   afirmación"): escribir una afirmación conocida del corpus (ej. sobre
   FAISS o BM25) → mostrar la clasificación, la cita exacta con el
   fragmento, y el JSON de salida completo.
2. **Subir un PDF nuevo** (pestaña "Analizar documento" → "Subir un
   PDF"): subir el PDF de prueba, dejar que extraiga afirmaciones,
   mostrar el resumen por nivel de evidencia y al menos un caso de
   `evidencia_parcial` o `evidencia_no_localizada` para demostrar que el
   sistema **no** fuerza todo a "suficiente".

Si el tiempo apremia, priorizar el flujo 1 (más rápido, más control sobre
el resultado) y mencionar el flujo 2 solo de palabra.

**Nota de timing**: con `qwen/qwen3.5-9b` cada afirmación tarda ~10-25s en
promedio (P95 ~40-50s) en evaluarse — tener la consulta lista de antemano
y lanzarla justo al empezar a hablar de esta sección, para no quedarse en
silencio esperando.

## 4. Métricas (3 min)

Mostrar la tabla de `DOCUMENTO_TECNICO.md` sección 6 (Recall@5, MRR,
exactitud de clasificación) y la comparación línea base (Fase 2, solo
semántico) vs. mejorada (Fase 3, híbrido) — este es el dato más fuerte:
la mejora de recuperación se traduce directamente en una mejora grande de
clasificación final, no es una mejora aislada sin impacto real.

Mencionar explícitamente la verificación del Recall@5 (ablation +
corpus duplicado con distractores) — evita que suene a número inflado.

## 5. Seguridad (2 min)

Mostrar la tabla SEC01-SEC07 de `DOCUMENTO_TECNICO.md` sección 5. Elegir
1-2 casos para explicar con un poco más de detalle (recomendado: SEC01,
porque es fácil de entender en 30 segundos — "si alguien le dice al
sistema que ignore sus instrucciones, el sistema lo ignora a él, no al
revés" — y SEC05, porque conecta directo con el problema de la sección 1:
no alucina citas).

Mencionar de paso que se encontraron y arreglaron 2 bugs reales durante
este trabajo (no solo "todo funcionó a la primera") — da credibilidad.

## 6. Conclusiones (1 min)

Cerrar con el patrón central del proyecto, en una frase: **cuando el LLM
falla, la solución casi nunca fue ajustarle el prompt — fue escribir un
chequeo de código que no depende de que se comporte bien.** Y que cada
arreglo se verificó contra el sistema real, no solo en aislamiento.

---

## Preguntas esperables (preparar respuesta corta)

- **"¿Por qué no usan GPT-4/Claude en vez de un modelo local?"** — Costo y
  privacidad durante desarrollo; el cliente habla REST directo
  (`src/agent/llm_client.py`), cambiar de proveedor es solo variables de
  entorno, no código (siempre que el proveedor soporte `response_format:
  json_schema`).
- **"¿Qué tan confiable es el Recall@5 de ~95%?"** — Verificado con
  ablation (semántico-solo vs. léxico-solo vs. híbrido) y con el corpus
  duplicado a 20 documentos con distractores reales; no se sostiene por
  un solo truco.
- **"¿Qué pasa si alguien sube un PDF malicioso?"** — SEC06: se valida
  tipo, tamaño, páginas, cifrado y JavaScript embebido antes de procesar
  nada; además texto invisible (SEC02) se filtra en la extracción.
- **"¿Qué falta?"** — Ver `TODO.md`/`STATUS.md`: detección de nombres
  propios en logs (bloqueada por spaCy en este entorno), y la limitación
  de recuperación en afirmaciones compuestas entre documentos no
  relacionados (ver `DOCUMENTO_TECNICO.md` sección 7).
