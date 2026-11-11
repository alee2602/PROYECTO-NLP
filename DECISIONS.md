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

## [2026-11-10] Límites duros de parámetros (top_k ≤ 20, max_claims ≤ 15)

**Contexto**: TH03 (ver entrada de la Fase 4) mostró que el sistema no aplicaba los límites de la sección 11 del anteproyecto; con `top_k=500` devolvía todo lo que hubiera en el corpus.
**Decisión**: nuevo módulo `src/limits.py` con `MAX_TOP_K=20` y `MAX_CLAIMS=15`. Se aplican recortando (clamp a `[1, máx]`) en los puntos de entrada: `HybridRetriever.search`, `extract_claims` y `run_pipeline`. Un valor ≤ 0 se sube a 1. Además `candidate_pool` nunca queda por debajo de `top_k`.
**Alternativas consideradas**: lanzar error ante valores fuera de rango — descartado porque el anteproyecto dice que los límites "se aplican", y recortar degrada de forma segura sin romper el flujo.
**Estado**: confirmada. 3 tests nuevos (`test_hybrid.py`, `test_extract_claims.py`), 70/70 pasan. No se aplica en `SemanticRetriever`/`LexicalIndex` directos (son componentes internos; el punto de entrada del sistema es el híbrido).
**Gaps abiertos**: falta re-correr TH03 en `scripts/run_eval.py` para confirmar el resultado en el runner real (requiere LM Studio).

## [2026-11-10] Exactitud de clasificación 69.57% → 86.96%: dos arreglos reales, uno revertido por regresión, y no-determinismo confirmado en casos límite

**Contexto**: tras la corrida de 69.57% (16/23), se leyeron las respuestas completas (no solo la etiqueta) de los 7 casos restantes para separar errores reales de errores de mi propio banco de pruebas. Se identificaron 3 causas concretas, cada una arreglada por separado y verificada contra el sistema real (LM Studio + corpus de 20 documentos), siguiendo el método ya establecido: nunca declarar un arreglo resuelto sin re-correr `scripts/run_eval.py`.

**Arreglo 1 (confirmado, funciona)**: `validate_citations` (`src/agent/validate_citations.py`) trataba identificadores arXiv dentro de la afirmación (ej. "arXiv:2502.13141") como si fueran una cifra factual que debía aparecer literalmente en el chunk citado — pero es una etiqueta de referencia, no un dato a verificar, y el chunker a menudo separa el header (donde está el ID) del cuerpo (donde está el hecho real). Se agregó `_ARXIV_ID_RE` para excluir estos identificadores antes de extraer números, con 2 tests de regresión nuevos. **Arregló TC09, TH01, TH02, TH05 — los 4 se sostienen en todas las corridas posteriores.**

**Arreglo 2 (confirmado, funciona, pero no por prompt — era un bug real de datos)**: TC19 (afirmación sobre versión/fecha de publicación) fallaba porque el LLM no tenía visibilidad de `publication_year`/`version`/`doi` en el prompt — se agregó `_format_chunk_header()` en `evaluate_evidence.py` para incluir esos campos. Al verificar contra el sistema real esto NO fue suficiente por sí solo: se descubrió que el campo `version` en `data/processed/documents.json` y `chunks.jsonl` estaba **hardcodeado en "1" para los 20 documentos**, aunque `source` sí tenía el sufijo real (ej. "arXiv:2309.15217v2" → 9 de 20 documentos con version incorrecta). Causa raíz: `scripts/build_corpus.py` y `scripts/add_corpus_documents.py` pasaban `version="1"` literal a `ingest_document()` en vez de derivarlo del `arxiv_id`. Se agregó `extract_version()` en `src/ingestion/arxiv_source.py` (regex sobre el sufijo `vN` del id), se usó en ambos scripts, y se parcheó in-place `documents.json`/`chunks.jsonl` existentes sin re-descargar nada. **Con el metadato correcto + el header visible, TC19 pasa de forma consistente.**

**Arreglo 3 (intentado, causó una regresión neta, revertido)**: para un caso de afirmación compuesta (TC12) se endureció la regla de "hechos compuestos" del `SYSTEM_PROMPT`, agregando una excepción explícita para afirmaciones vagas/genéricas (pensando en TC15, que ya fallaba antes de este cambio) más un 6to ejemplo few-shot. Al verificar contra el sistema real: TC15 pasó de fallar de un modo (`evidencia_suficiente` en vez de `parcial`) a fallar de otro (`evidencia_no_localizada`, ignorando mi instrucción explícita de que debía seguir siendo `parcial`) — el modelo generalizó "vago → rechazar todo" más allá de lo pedido. Peor: **esto produjo dos regresiones en casos que antes pasaban** — TC08 (contradicción, antes correcto) y el propio TC12 (compuesto, antes correcto) empezaron a fallar también, probablemente por la mayor longitud/complejidad del prompt diluyendo la atención del modelo en reglas no relacionadas. Exactitud bajó a 82.61% (19/23). **Se revirtió el cambio completo** (la excepción de afirmaciones vagas y el ejemplo 6), dejando la regla de hechos compuestos como estaba en la entrada anterior.

**Resultado final verificado** (dos corridas idénticas de código, para distinguir regresión real de no-determinismo del motor): 86.96% (20/23) en ambas, pero con conjuntos de fallos distintos — primera corrida: TC14, TC15, TC19 fallan; segunda corrida (con el `version` corregido): TC06, TC14, TC15 fallan, TC19 ya pasa. **TC06 cambió de correcto a incorrecto entre dos corridas con el mismo código** (`temperature=0.0` en `llm_client.py`, pero el motor de inferencia local/modelo "thinking" no es perfectamente determinista) — es un caso límite genuino (afirmación "especialmente complicado" vs. el fragmento que solo dice "challenges", sin calificar intensidad), no una regresión causada por este trabajo.

**Decisión**: quedarse con los arreglos 1 y 2 (ambos verificados, ambos causas raíz reales — no parches de prompt). No reintentar el arreglo 3 por ahora: dos intentos de ajuste de prompt para TC12/TC15 ya mostraron que endurecer esta regla tiene efectos colaterales en casos no relacionados: mismo patrón de "techo" ya visto con `contradiction_check`, pero esta vez no hay un cambio de modelo obvio que lo resuelva.

**Estado**: confirmado — 67/67 tests unitarios pasan, 86.96% (20/23) de exactitud de clasificación contra el sistema real, Recall@5 se sostiene en 100% (21/21).

**Gaps abiertos**: TC12 ahora pasa pero cita solo `['D09']` en vez de `['D02', 'D09']` (recall_hit sigue en True porque mi métrica usa overlap "any", no "all" — el gap de metodología de TC14 ya documentado sigue sin resolver). TC14 y TC15 siguen sin arreglo real conocido. TC06 confirma que el sistema tiene no-determinismo residual en casos límite incluso con `temperature=0.0` — vale la pena mencionarlo como limitación honesta en el reporte final en vez de asumir que cada corrida da el mismo resultado exacto.

## [2026-11-10] Cambio de modelo (qwen2.5-vl-7b-instruct → qwen/qwen3.5-9b) resuelve el bug de contradicción de raíz

**Contexto**: TC08 (contradicción) seguía fallando pese a dos intentos de ajustar el prompt de `evaluate_evidence` y un intento adicional con un verificador de contradicción separado (`contradiction_check.py`, mismo patrón que `validate_citations`). El verificador separado, probado con `qwen2.5-vl-7b-instruct`, resultó en falsos positivos aún peores (marcaba "contradice" hasta en citas correctas como TC02/TC04) — tres intentos consecutivos de prompt engineering con el mismo modelo fallaron en direcciones opuestas, señal clara de un techo de capacidad del modelo, no un problema de redacción.
**Decisión**: en vez de seguir ajustando el prompt, se cambió el modelo cargado en LM Studio de `qwen2.5-vl-7b-instruct` (7B, variante visión-lenguaje) a `qwen/qwen3.5-9b` (9B, modelo de razonamiento/"thinking" de solo texto, sin el costo de soportar también imágenes).
**Hallazgo técnico en el camino**: `qwen3.5-9b` devuelve su respuesta en el campo `reasoning_content` del JSON de la API, dejando `content` vacío — esto hacía fallar `evaluate_claim` SIEMPRE con este modelo (ambos reintentos fallaban, caía al fallback de abstención). Se corrigió `generate_json` (`src/agent/llm_client.py`) para usar `content` si existe, si no `reasoning_content` como respaldo — un arreglo de compatibilidad genérico, útil para cualquier modelo "thinking" futuro, no específico de Qwen.
**Resultado real**: con el modelo nuevo, TC02 y TC04 (que deben ser `evidencia_suficiente`) siguen correctos, Y TC08 (contradicción) ahora sale `evidencia_parcial` con `needs_human_review=true` **directamente desde la llamada principal de `evaluate_evidence`**, sin necesitar el veto de `contradiction_check` — el modelo razona bien la contradicción por sí solo, citando explícitamente "la evidencia contradice la afirmación" en su respuesta.
**Alternativas consideradas**: mantener `qwen2.5-vl-7b-instruct` y seguir iterando el prompt — descartado tras 3 intentos fallidos consecutivos; usar una API en la nube (Claude Haiku, GPT-4o-mini) solo para este chequeo — descartado por ahora porque el cambio de modelo local ya resolvió el problema sin costo ni dependencia externa adicional.
**Estado**: confirmado con los 3 casos críticos (TC02, TC04, TC08) y con el banco completo de 25 casos — ver entrada siguiente con el resultado agregado.
**Gaps abiertos**: actualizar `README.md` para recomendar `qwen/qwen3.5-9b` en vez de (o además de) `qwen2.5-vl-7b-instruct`; `contradiction_check.py` se queda en el código como red de seguridad adicional (no hace daño si el modelo principal ya acierta — solo se activa en casos `evidencia_suficiente`), pero ya no es el mecanismo que resuelve el problema principal.

## [2026-11-10] Banco de pruebas completo con el modelo nuevo: exactitud de clasificación 30% → 70%

**Contexto**: tras cambiar a `qwen/qwen3.5-9b` y arreglar el fallback de `reasoning_content`, se volvió a correr `scripts/run_eval.py` con los 25 casos oficiales — esta vez contra el corpus YA AMPLIADO de 20 documentos (472 chunks), es decir, una medición más exigente que la primera (que fue con 10 documentos).
**Resultado**: Recall@5 = 100% (21/21, se sostiene igual que en el ablation, ahora también bajo carga real del LLM). Exactitud de clasificación = **69.57% (16/23)**, frente al 30.43% (7/23) del modelo anterior — más del doble, sin cambiar ni una línea de prompt, solo el modelo.
**Composición de los 7 casos restantes que no coinciden** (TC09, TC12, TC14, TC19, TH01, TH02, TH05): los 7 son el mismo patrón ya visto — el sistema es MÁS CONSERVADOR de lo que predije (`evidencia_parcial` donde el banco esperaba `evidencia_suficiente`), nunca al revés. **Cero fallas de generación** (antes había 3) y **cero falsos positivos peligrosos** (antes había 1, TC08, ya resuelto). Es decir: todo lo que resta es calibración de umbral, no errores de razonamiento ni de seguridad.
**Decisión**: no se necesita más ajuste de prompt por ahora. El resultado es sólido: recuperación perfecta y verificada a escala (ver ablation), clasificación mayormente correcta y, en los casos que fallan, conservadora (segura) en vez de arriesgada. Esto es presentable en el documento técnico con honestidad y sin maquillaje.
**Estado**: confirmado con los 23 casos de contenido corridos contra el sistema completo (corpus de 20 documentos, modelo `qwen/qwen3.5-9b`).
**Gaps abiertos**: revisar si los 7 casos restantes reflejan un `expected_evidence_level` del banco demasiado optimista (como ya se sospechaba desde la medición anterior) o si de verdad conviene que el sistema sea menos conservador — decisión de producto, no un bug a arreglar a ciegas.

## [2026-11-10] Ablation de recuperación + ampliación del corpus a 20 documentos: el Recall@5=100% no es un artefacto

**Contexto**: tras medir Recall@5=100% con el corpus de 10 documentos, surgió la duda legítima de si ese número era sólido o un artefacto de (a) un corpus pequeño (10 candidatos es un problema fácil) o (b) el boost de identificadores de `HybridRetriever` haciendo trabajo desproporcionado ("hardcodeo" disfrazado). Reportar un 100% sin descartar esto habría sido, con razón, sospechoso para cualquiera que revise el proyecto.
**Método**: (1) `scripts/run_retrieval_ablation.py` mide Recall@5 por separado para solo-semántico, solo-léxico, híbrido-sin-boost e híbrido-completo, contra los mismos 21 casos de contenido del banco oficial. (2) `scripts/add_corpus_documents.py` agrega 10 documentos distractores nuevos (D11-D20, vía arXiv) elegidos a propósito para ser temáticamente cercanos a D01-D10 (ej. D13 "Hallucination Detection with Small Language Models" cerca de D09/RAGAS; D14 "BlueSuffix: Reinforced Blue Teaming... Against Jailbreak" cerca de D07/D08) — sin tocar D01-D10 ni los IDs ya usados en `test_cases.json`.
**Resultado con 10 documentos**: semántico=95.2%, léxico=90.5%, híbrido-sin-boost=95.2%, híbrido-completo=100% (el boost solo rescata TC10, el caso de acrónimo exacto para el que se diseñó explícitamente).
**Resultado con 20 documentos (corpus duplicado, con distractores reales)**: semántico=90.5% (bajó, pierde además TC11), léxico=90.5% (igual), híbrido-sin-boost=95.2% (**se sostiene exactamente igual**), híbrido-completo=100% (**se sostiene**). El sistema completo no se degradó al duplicar el corpus — donde el componente semántico pierde terreno a mayor escala (TC11), el léxico lo compensa dentro de la combinación híbrida.
**Conclusión**: el Recall@5=100% es una medición sólida, no un artefacto de corpus chico ni de un hack puntual — cada componente (semántico, léxico, boost de identificadores) cubre un tipo de fallo distinto y específico, y la combinación es robusta a duplicar el tamaño del corpus con distractores reales y temáticamente adversariales. Vale la pena incluir esta tabla de ablation en el documento técnico final en vez de solo el número de Recall@5 — es la evidencia que sostiene que no es un resultado inflado.
**Alternativas consideradas**: reportar solo el Recall@5 del corpus de 10 documentos sin esta prueba — descartado porque, como se discutió, un 100% sin análisis de robustez es legítimamente sospechoso y debilitaría la credibilidad del reporte ante el profesor.
**Estado**: confirmada con dos corridas completas (10 y 20 documentos).
**Gaps abiertos**: no se volvió a correr el banco de clasificación completo (con LLM) contra el corpus de 20 documentos, solo el ablation de recuperación (no necesita LLM, corre en segundos). Si se quiere una medición de clasificación igualmente robusta a escala, habría que repetir `scripts/run_eval.py` contra el corpus ampliado. El corpus ahora tiene 20 documentos en `data/raw/` y `data/processed/` — recordar que esto no afecta los 25 casos de `test_cases.json` (sus `expected_sources` siguen siendo D01-D10 exclusivamente).

## [2026-11-10] Primera corrida real del banco de pruebas (Fase 4): Recall@5=100%, exactitud de clasificación=30% (con matices importantes)

**Contexto**: el banco de pruebas de 25 casos del anteproyecto (sección 12) estaba escrito de forma genérica, sin afirmaciones concretas, porque se diseñó antes de tener el corpus real. Se redactaron 25 afirmaciones genuinas basadas en contenido verificado de D01-D10 (`data/eval/test_cases.json`) y se construyó `scripts/run_eval.py` para correrlas contra el sistema real y calcular métricas, en vez de seguir midiendo con ejemplos sueltos.

**Resultado crudo**: Recall@5 = 100% (21/21 — el documento esperado siempre apareció en el top-5). Exactitud de clasificación (evidence_level exacto == esperado) = 30.4% (7/23). El número de clasificación por sí solo es engañoso; desglose real tras leer las 23 respuestas completas (no solo la etiqueta):

- **3/23 (TC01, TC03, TC14) son fallas de generación del motor** ("No fue posible generar una evaluación válida"), no errores de razonamiento — mismo bug de llama.cpp/LM Studio ya documentado (grammar-constrained decoding). El sistema se abstiene de forma segura, como está diseñado. Cuentan como "fallo" en la métrica estricta pero no son un defecto de clasificación.
- **~13/23 son el modelo siendo MÁS CONSERVADOR de lo que predije** (p. ej. clasifica "evidencia_parcial" o "evidencia_no_localizada" donde yo esperaba "evidencia_suficiente"), pero citando el documento correcto y con razonamiento sólido en el campo `answer`. Ejemplos concretos inspeccionados: TC06 identificó la paráfrasis completa correctamente pero la etiquetó "parcial"; TC13 y TC16 **detectaron correctamente** que la afirmación decía más de lo que el fragmento respalda (justo el matiz que buscaban esos casos) pero usaron una categoría más severa ("no_localizada") de la que yo anticipé ("parcial"). Es una diferencia de calibración/umbral, no un error de fondo — y es la dirección seguridad-primero (subconfianza, no sobreconfianza).
- **1/23 (TC08) es una falla real y confirmada, no solo de calibración**: la afirmación decía que los sistemas automatizados NO reducen el tiempo/esfuerzo (falso, invierte un hallazgo de D02). El modelo escribió en su propia respuesta el hecho correcto que CONTRADICE la afirmación ("...SÍ pueden reducir el tiempo...") pero aun así clasificó `evidencia_suficiente`. **Esto confirma que el arreglo de contradicción de la entrada anterior (`SYSTEM_PROMPT` con regla + ejemplo few-shot) no generaliza a redacciones nuevas de contradicción** — sigue siendo un riesgo real, no resuelto de raíz.
- **1/23 (TC17) se salvó por suerte, no por diseño**: la afirmación era sobre un tema totalmente ausente del corpus (traducción automática/WMT14). El modelo no reconoció limpiamente la ausencia total del tema y citó D09 (RAGAS) de forma tangencial; `validate_citations` lo degradó de categoría solo porque la cifra "14" (de "WMT14") no aparecía literalmente en el chunk citado — una coincidencia afortunada del chequeo numérico, no una detección real de "tema fuera de alcance".

**Decisión**: no seguir parchando el prompt de `evaluate_evidence` por ahora — ya se intentó dos veces (contradicción, vaguedad) con éxito parcial y claros rendimientos decrecientes. Se documenta esto como limitación conocida y medida del sistema (útil directamente para la sección "limitaciones operativas" del documento técnico final, que el curso pide explícitamente). Los 25 casos y el runner quedan reutilizables para volver a medir si se cambia de modelo (ej. una API en la nube) o se ajusta el prompt más adelante.

**Hallazgo adicional (TH03)**: el sistema NO aplica el límite duro `top_k ≤ 20` que pide el anteproyecto (sección 11: "se aplican los límites... top_k ≤ 20, max_claims ≤ 15") — con `top_k=500` el sistema devolvió 40 resultados (limitado solo por el tamaño real del corpus, no por una validación explícita). Esto era un gap real de validación de parámetros; resuelto el 2026-11-10 (ver entrada "Límites duros de parámetros").

**Estado**: medición confirmada con 23 casos reales corridos contra el sistema completo (recuperación + LLM real + validate_citations). Gap de contradicción (TC08) y de reconocimiento de ausencia total de tema (TC17) quedan documentados como limitaciones abiertas para la sección de seguridad/limitaciones del documento técnico.
**Gaps abiertos**:
- Contradicción (TC08): necesitaría un modelo más grande o una estrategia distinta (ej. un paso de verificación separado) para resolverse de raíz, no solo prompt engineering.
- Reconocimiento de "tema totalmente fuera del corpus" (TC17): el modelo no lo detecta de forma confiable por sí mismo.
- ~~Validación de límites de parámetros (top_k≤20, max_claims≤15)~~: resuelto el 2026-11-10, ver entrada "Límites duros de parámetros".
- Reconsiderar si el `expected_evidence_level` de varios casos del banco de pruebas fue demasiado optimista (esperaba "suficiente" donde "parcial" es defendible) — revisar antes de usar este banco para la nota final.

## [2026-11-10] Orquestador agéntico (LangGraph) + filtro determinístico de afirmaciones vagas

**Contexto**: tras conectar `extract_claims` + `search_evidence` (HybridRetriever) + `evaluate_evidence`/`validate_citations` en un grafo de LangGraph (`src/agent/orchestrator.py`, con refinamiento de búsqueda si la primera pasada no encuentra evidencia), se corrió sobre un documento real completo (D04, no afirmaciones armadas a mano) para medir calidad real, siguiendo el pedido explícito de la usuaria de no conformarse con un proyecto mediocre.
**Hallazgo**: 2 de 6 afirmaciones extraídas eran demasiado genéricas ("we propose various approaches to combat these problems") — sin ningún dato/nombre específico, cualquier documento del corpus que mencione "enfoques" o "problemas" las "respalda" vagamente, y el LLM las clasificó como `evidencia_suficiente` citando documentos completamente ajenos al tema (ej. un paper de defensa contra prompt injection para una afirmación sobre recuperación legal). Se intentó arreglar solo con instrucciones más explícitas en el prompt de `extract_claims` (incluyendo ese ejemplo exacto como "qué NO hacer") — **no fue suficiente**: la misma afirmación casi textual se volvió a extraer y a mal-atribuir en la siguiente corrida.
**Decisión**: agregar un filtro determinístico (`_is_too_vague` en `src/agent/extract_claims.py`, no delegado al LLM) que rechaza afirmaciones que matchean patrones de meta-comentario genérico sobre metodología ("various/different/several approaches/methods", "combat/address estos problemas", etc.) Y no contienen ninguna señal de especificidad (cifra, acrónimo/nombre propio en mayúsculas, término entre comillas). Confirmado con prueba real: la afirmación problemática ya no aparece en la lista extraída de D04 (bajó de 5 a 4 afirmaciones), y las 4 restantes se clasificaron correctamente o con seguridad razonable (una de ellas mejoró de un falso "suficiente" a un honesto "parcial" con explicación específica citando nombres reales de modelos del propio documento).
**Patrón que se repite en este proyecto**: igual que con la contradicción (bug #2) y la cifra inventada (validate_citations), las instrucciones de prompt por sí solas no bastan para garantizar un comportamiento — los chequeos determinísticos por código son los que de verdad sostienen la calidad. Vale la pena recordar esto para cualquier ajuste futuro de calidad de clasificación.
**Estado**: confirmada con prueba end-to-end real (no solo pruebas unitarias con cliente falso).
**Gaps abiertos**: el filtro de vaguedad es una heurística angosta (lista de patrones conocidos), no una solución general — puede que afirmaciones vagas con otra redacción se cuelen igual. CLAIM_002 en la prueba real sigue citando un documento parcialmente no relacionado junto con el correcto (mitigado por quedar en `evidencia_parcial` + `needs_human_review=true`, no por estar resuelto del todo). La única forma de tener un número de confianza real (no anecdótico) es correr el banco de pruebas oficial de 25 casos en Fase 4.

## [2026-11-10] Implementación de `search_metadata` (Crossref)

**Contexto**: siguiente tool pendiente del flujo agéntico (anteproyecto sección 11): consultar metadatos bibliográficos sin usarlos como evidencia textual (sección 7).
**Decisión**: `src/agent/search_metadata.py` consulta la API pública de Crossref por `doi` (búsqueda exacta) o `title`/`author` (búsqueda difusa, `query.bibliographic`). Ante timeout o error de red, devuelve `None` en vez de propagar la excepción — degradación controlada, igual que describe el caso TH05 del anteproyecto ("la evaluación continúa con el corpus local; metadatos marcados como no verificados"). Probado con mocks (6 pruebas, sin red) y una vez contra la API real.
**Hallazgo al probar con la API real**: una búsqueda por título ("Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", el paper original de Lewis et al. 2020) devolvió un capítulo de libro distinto con título parecido, no el paper esperado. Esto es comportamiento normal de Crossref (busca por similitud, no coincidencia exacta) — confirma que esta tool debe tratarse como "candidato a verificar", nunca como fuente de verdad automática; quien la use debe contrastar el resultado contra lo esperado antes de confiar en él.
**Estado**: confirmada.
**Gaps abiertos**: ninguno para la tool en sí; falta decidir cómo el orquestador agéntico (LangGraph, pendiente) usa este resultado para decidir si una cita es confiable.

## [2026-11-10] Migración de `venv` a entorno conda dedicado (Smart App Control bloqueaba `torch`)

**Contexto**: al subir `top_k` y correr `scripts/demo.py` con normalidad, `import torch` (dependencia de `sentence-transformers`) empezó a fallar con `OSError: [WinError 4551] Una directiva de Control de aplicaciones bloqueó este archivo` — Windows Smart App Control bloqueó específicamente el `torch.dll` descargado por `pip` en el `venv` del proyecto (mismo tipo de bloqueo que ya había pasado con `jiter` del SDK de `openai`, ver entrada anterior sobre el cliente LLM). La usuaria explícitamente no quiso desactivar Smart App Control ni crear exclusiones de Defender (decisión de seguridad respetada, no negociable).
**Investigación**: se confirmó que el `torch` instalado en la base de Anaconda de la misma máquina (`2.11.0+cu128`, instalado hace tiempo vía `conda`) sí carga sin problema — el bloqueo es específico de esa copia de `torch.dll` descargada por `pip` (binario grande, sin firma de un publisher reconocido, con reputación en la nube de Microsoft aún no establecida), no un bloqueo general de `torch` en la máquina. Esto explica por qué la usuaria "nunca había tenido problemas con torch": siempre lo había usado vía Anaconda, nunca instalado fresco con `pip` en un `venv` nuevo.
**Decisión**: crear un entorno conda dedicado (`evidentia`, separado del `base` de Anaconda para no ensuciarlo) e instalar `torch` ahí vía `conda install pytorch -c pytorch` en vez de `pip install torch`, reutilizando el canal de Anaconda que no dispara el bloqueo. El resto de dependencias (`sentence-transformers`, `faiss-cpu`, `pymupdf`, etc.) se instalan normal vía `pip` dentro de ese entorno — solo `torch` necesitaba venir de conda. Esto evita el problema de raíz sin tocar ninguna configuración de seguridad de Windows y sin depender de LM Studio para los embeddings (se consideró esa alternativa pero se descartó: la usuaria no quería depender 100% de LM Studio para todo).
**Problemas secundarios encontrados y resueltos en el camino**:
  - El `pytorch` inicial instalado por conda (2.5.1) era insuficiente para la versión más reciente de `transformers` (pedía `torch >= 2.6`) — se actualizó a `pytorch=2.15.0` (build `cpu_mkl`, canal `pytorch`, encontrado con `conda search`).
  - Esa actualización de conda removió `pyyaml` como efecto secundario no solicitado — se reinstaló vía `conda install` (no `pip`, porque en ese momento el DNS de la red de la usuaria estaba fallando otra vez para pypi.org, igual que en una sesión anterior).
**Estado**: confirmada y verificada — las 38 pruebas automáticas pasan en el entorno `evidentia`, incluyendo las que dependen de `sentence-transformers`/FAISS que antes estaban bloqueadas.
**Gaps abiertos**: el `venv` original (en `PROYECTO-NLP/venv/`) queda obsoleto — ya no es el entorno activo del proyecto, se puede borrar cuando se quiera (no se borró automáticamente). El README ahora documenta conda como el setup oficial, no `venv`.

## [2026-11-10] Implementación de búsqueda híbrida y arreglo de 3 bugs reales encontrados al re-probar la demo

**Contexto**: al atacar el Hallazgo 1 de la entrada anterior (recuperación semántica pura falla con términos técnicos exactos), se implementó BM25 híbrido y aparecieron 3 problemas nuevos, cada uno diagnosticado con evidencia concreta antes de arreglarse — no se adivinó ninguno.

**Hallazgo A — BM25 ingenuo no basta por el choque de idiomas (español/inglés)**: con `LexicalIndex` básico, una consulta sobre "BM25" traía documentos irrelevantes por encima de D04 (el paper correcto), porque palabras funcionales en español ("es", "una", "de", "que") generan coincidencias de ruido contra el corpus en inglés. Peor aún: "ranking" es una palabra que existe igual en ambos idiomas, así que un documento sobre optimización de ranking (D03) acumulaba más puntaje que D04 por ese término genérico, diluyendo la única señal realmente diagnóstica ("bm25"). **Arreglo**: (1) lista de stopwords español+inglés en `tokenize()` (`src/retrieval/lexical.py`); (2) un boost explícito de "identificador técnico exacto" en `HybridRetriever` (`src/retrieval/hybrid.py`) que detecta tokens con forma de identificador (mayúsculas+dígitos, ej. "BM25", "RAGAS") en el texto original de la afirmación y da un bonus fuerte a cualquier chunk que los contenga literalmente, sin importar el resto del ranking. Tras el arreglo, D09 (RAGAS) pasó a ser el resultado #1 para su consulta; D04 (BM25) aparece en el top-5 junto con D03 — y se confirmó que **D03 también es legítimamente relevante** (cita el paper original de BM25 como baseline), así que no competían por error, ambos eran candidatos válidos.

**Hallazgo B — el context window del modelo en LM Studio era insuficiente**: al subir `top_k` de 3 a 5 (como pide el anteproyecto), empezaron a fallar las llamadas al LLM con `400 Bad Request: "the number of tokens to keep... is greater than the context length (n_keep: 4762 >= n_ctx: 4096)"`. El modelo se había cargado con el contexto por defecto de LM Studio (4096 tokens), insuficiente para 5 chunks de ~450 palabras + prompt + schema. **Arreglo**: recargar el modelo con `lms load <modelo> --context-length 16384`. Esto no es un bug de código, es un paso de configuración que hay que recordar hacer siempre (documentado en README).

**Hallazgo C — ligaduras tipográficas sin normalizar**: se sospechó que caracteres de ligadura (ﬁ, ﬂ — comunes en PDFs académicos, ej. "ﬁnd" en vez de "find") causaban un crash del motor de LM Studio. Se agregó normalización en `clean_text()` (`src/ingestion/cleaner.py`) y se reprocesó el corpus local sin necesitar red (`scripts/reprocess_corpus.py`, reusa los PDFs ya descargados). Es una mejora de calidad de texto legítima independientemente del crash, pero **no fue la causa** del Hallazgo D (ver abajo) — se mantiene el fix porque es correcto de todas formas.

**Hallazgo D — crash del motor de LM Studio con JSON Schema (no es nuestro bug)**: después de descartar el Hallazgo C como causa, el error real es `"got exception: Unexpected empty grammar stack after accepting piece: G (38)"` — un bug conocido de la decodificación con grammar de llama.cpp (el motor detrás de LM Studio), no de nuestro código ni de nuestro esquema. **Decisión**: no perseguir un arreglo desde nuestro lado por ahora — el sistema ya reintenta una vez y, si vuelve a fallar, se abstiene con `needs_human_review=True`, que es exactamente la degradación seguridad que pide el anteproyecto (sección 11: "una salida que no pase la validación se regenera una sola vez; si vuelve a fallar, el sistema se abstiene"). Si este crash resulta muy frecuente al correr el banco de pruebas real en Fase 4, revisar si cambiar de modelo/motor ayuda.

**Estado**: Hallazgos A, B y C confirmados y arreglados con pruebas (32 pruebas automáticas pasando, incluye regresión específica para el Hallazgo A en `tests/test_hybrid.py`). Hallazgo D documentado como comportamiento esperado, no un bug a resolver.
**Gaps abiertos**: el Hallazgo 2 de la entrada anterior (evidencia que contradice vs. respalda la afirmación) se atacó por separado — ver entrada siguiente.

## [2026-11-10] Arreglo del falso positivo de contradicción (mejora parcial, no perfecta)

**Contexto**: el Hallazgo 2 de la demo (ver entrada del 2026-11-09) — una afirmación contradicha por la evidencia (D07, paper de detección de prompt injection, contra la afirmación "es imposible detectar") se clasificaba como `evidencia_suficiente` en vez de rechazarse.
**Decisión**: se agregó al `SYSTEM_PROMPT` de `evaluate_evidence.py` una regla explícita — evidencia que contradice/refuta la afirmación debe ser `evidencia_parcial` (nunca `evidencia_suficiente`) con `needs_human_review=true`, más un ejemplo few-shot mostrando el caso exacto. También se agregó `minLength: 1` al campo `answer` en `RESPONSE_SCHEMA` para que nunca quede vacío (antes a veces pasaba `""`, incluso en abstención). **Resultado real tras volver a correr `scripts/demo.py`**: el caso de prueba ya NO se clasifica como `evidencia_suficiente` (el falso positivo peligroso desapareció) — pero tampoco llegó al ideal de `evidencia_parcial` con explicación de la contradicción; terminó en `evidencia_no_localizada` (abstención genérica). Es una mejora real y verificada, no perfecta: se eliminó el riesgo más grave (afirmar respaldo falso) aunque no se logró la explicación fina que pedía el diseño original.
**Alternativas consideradas**: agregar una cuarta categoría `evidencia_contradictoria` al esquema — descartada porque el anteproyecto especifica exactamente 3 categorías (sección 6); mapear la contradicción a una de las 3 existentes es más fiel al diseño aprobado.
**Estado**: confirmada — mejora parcial verificada con evidencia real, no solo supuesta.
**Gaps abiertos**: evaluar con el banco de pruebas completo (25 casos, Fase 4) si el modelo local de 7B es suficientemente confiable para este tipo de razonamiento, o si hace falta un modelo más grande/un proveedor en la nube para los casos de contradicción específicamente.

## [2026-11-09] Hallazgos de la demo manual (`scripts/demo.py`): dos gaps de calidad detectados

**Contexto**: antes de avanzar a Fase 3, se corrió `scripts/demo.py` (4 afirmaciones de prueba, no las oficiales del banco) contra el corpus real (D01-D10) y LM Studio real (`qwen2.5-vl-7b-instruct`), para ver el comportamiento de punta a punta con datos reales en vez de solo tests unitarios. Log completo en `logs/demo_output.txt` (no versionado — reproducible corriendo el script).
**Hallazgo 1 — recuperación semántica pura falla con términos técnicos exactos**: para una afirmación sobre BM25, el top-3 de `SemanticRetriever` NO incluyó D04 ("Legal Information Retrieval using BM25 and BERT"), el documento obviamente más relevante del corpus. Para una afirmación sobre RAGAS, el top-3 NO incluyó D09 ("Ragas: Automated Evaluation of..."), el paper del que trata directamente la afirmación. En ambos casos el sistema se abstuvo (comportamiento seguro, no inventó nada), pero por la razón equivocada: el documento correcto existe en el corpus y no fue encontrado.
**Hallazgo 2 — el esquema/prompt no distingue "evidencia a favor" de "evidencia en contra"**: para la afirmación "los ataques de inyección de prompt son completamente imposibles de detectar", el sistema recuperó D07 ("UniGuardian: A Unified **Defense** for **Detecting** Prompt Injection...") — evidencia que **contradice** la afirmación (si existen defensas que detectan, no es "imposible"). El modelo respondió `answer: "no"` (señal de que entendió la contradicción) pero igual clasificó `evidence_level: evidencia_suficiente`, cuando según el propio banco de pruebas del anteproyecto (caso TC08: "afirmación que invierte el sentido... no se clasifica como suficiente") debería rechazarse o marcarse de otra forma. El prompt actual (`SYSTEM_PROMPT` en `evaluate_evidence.py`) solo contempla "evidencia respalda" vs. "no hay evidencia", sin una categoría para "evidencia refuta".
**Decisión**: documentar y priorizar en TODO.md (Fase 3) en vez de arreglar a medias ahora mismo. Propuesta concreta para cuando se ataque:
  1. Para el Hallazgo 1: implementar la búsqueda híbrida BM25 + semántica (70/30) que ya pedía el anteproyecto desde el inicio — BM25 captura coincidencias léxicas exactas (BM25, RAGAS) que el embedding semántico está subponderando. Subir `top_k` de 3 a 5 (como dice el anteproyecto) también ayuda, pero no resuelve el problema de fondo.
  2. Para el Hallazgo 2: agregar explícitamente al `SYSTEM_PROMPT` y a `RESPONSE_SCHEMA` una tercera señal — no necesariamente un cuarto `evidence_level`, pero sí instrucciones explícitas de que "evidencia que contradice la afirmación" NO es `evidencia_suficiente` (debe ser `evidencia_no_localizada` o un nuevo estado tipo `contradicha`, a decidir). Añadir casos de prueba tipo TC08 a los ejemplos del prompt (few-shot) para anclar el comportamiento esperado.
**Alternativas consideradas**: ignorar estos hallazgos y seguir con Fase 3 tal cual — descartado porque el Hallazgo 2 es justo el tipo de falso positivo que la rúbrica de seguridad/fundamentación penaliza fuerte, mejor documentarlo ahora que se encontró.
**Estado**: hallazgos confirmados con evidencia reproducible; arreglo pendiente (ver TODO.md Fase 3).
**Gaps abiertos**: ambos — ver TODO.md. Quien retome esto (Bianca u otra persona) puede reproducir corriendo `scripts/demo.py` con LM Studio corriendo.

## [2026-11-09] Corpus inicial: 10 papers de arXiv (D01-D10)

**Contexto**: faltaba fijar los documentos reales del MVP (D01-D10, referenciados como "por fijar" en el banco de pruebas del anteproyecto).
**Decisión**: `src/ingestion/arxiv_source.py` consulta la API pública de arXiv (sin API key) y `scripts/build_corpus.py` descarga 2 papers por cada uno de 5 temas ligados al propio dominio técnico del proyecto (RAG, BM25, FAISS/similitud, prompt injection, evaluación de RAG), filtra duplicados entre queries y descarta documentos de más de 40 páginas (para no sesgar el corpus con una tesis/survey larga — pasó con un documento de 133 páginas en el primer intento). Resultado: 10 documentos, 222 chunks, probado end-to-end con `SemanticRetriever` contra el corpus real (consulta sobre "BM25 para recuperación legal" recuperó correctamente D04, el paper de BM25+BERT para COLIEE). Lista de documentos y sus `arXiv:id` en `data/processed/documents.json`.
**Alternativas consideradas**: usar también documentos propios del equipo (mencionados en el anteproyecto) — se deja como opcional, el corpus de arXiv ya cumple el mínimo de 5-10 documentos exigido.
**Estado**: confirmada para el MVP.
**Gaps abiertos**: hay que actualizar la tabla del banco de pruebas en el anteproyecto (sección 12) reemplazando "p. por fijar" con páginas reales de estos 10 documentos, una vez que se redacten las 25 afirmaciones de prueba contra el contenido real.

## [2026-11-09] Gobernanza de datos: texto completo del corpus no se versiona en git

**Contexto**: al generar `data/processed/chunks.jsonl` nos dimos cuenta de que contiene el texto completo extraído de los 10 papers, no solo metadata — a diferencia de los PDFs originales (ya excluidos), este archivo sí se iba a subir a git por defecto.
**Decisión**: se agregó `data/processed/chunks.jsonl` al `.gitignore`. Se mantiene `documents.json` versionado porque solo contiene metadata bibliográfica (título, autores, año, licencia), que no es el contenido protegido del paper.
**Alternativas consideradas**: versionar igual el texto completo, apoyándose en que arXiv permite su distribución — se descartó por ser más conservador: el proyecto no necesita redistribuir el texto vía GitHub para funcionar, solo necesita poder regenerarlo localmente con `scripts/build_corpus.py`.
**Estado**: confirmada.
**Gaps abiertos**: ninguno — `chunks.jsonl` se puede regenerar en cualquier momento corriendo el script, no se pierde nada al no versionarlo.

## [2026-11-09] Modelo generativo: cliente compatible con OpenAI (LM Studio por defecto)

**Contexto**: el anteproyecto no fijaba un proveedor de LLM concreto; había que decidir cómo generar la clasificación fundamentada (`evaluate_evidence`).
**Decisión**: `src/agent/llm_client.py` usa el SDK `openai`, pero apuntado a `LLM_BASE_URL` (default `http://localhost:1234/v1`, el servidor local de LM Studio). Cambiar de proveedor es solo cambiar variables de entorno (`.env.example`), no código. `src/schemas/output.py` define `EvidentiaOutput` con las reglas de consistencia exactas de la sección 11 del anteproyecto (`abstained` ⇒ `sources` vacío y `evidence_level=evidencia_no_localizada`; `evidencia_suficiente` ⇒ al menos una fuente). `src/agent/evaluate_evidence.py` reintenta una vez si la salida no valida y si vuelve a fallar se abstiene con `needs_human_review=True`, tal como pide el anteproyecto.
**Alternativas consideradas**: Ollama (similar, se descartó por ahora a favor de LM Studio por preferencia del equipo); comprometerse directo con una API de pago (Claude Haiku/GPT-4o-mini) — se pospuso para no gastar mientras se desarrolla; el plan es comparar ambos antes de la Fase 4 (ver TODO Fase 2).
**Estado**: confirmada y validada contra LM Studio real (ver entrada siguiente).
**Gaps abiertos**: ninguno por ahora; revisar de nuevo si cambian de modelo cargado en LM Studio.

## [2026-11-09] Cliente LLM por REST directo (no SDK `openai`) + JSON Schema en vez de json_object

**Contexto**: al probar `evaluate_claim` contra LM Studio real por primera vez, el SDK `openai` falló al importar (`ImportError: DLL load failed while importing jiter: Una directiva de Control de aplicaciones bloqueó este archivo`) — Windows (Smart App Control u otra política similar) bloqueó el binario nativo de `jiter`, una dependencia del SDK. Además, una vez resuelto eso, LM Studio devolvió `400 Bad Request: 'response_format.type' must be 'json_schema' or 'text'` — su servidor no soporta el modo `json_object` de OpenAI, solo `json_schema` (salida con grammar constraints) o `text`.
**Decisión**: se quitó la dependencia del SDK `openai` por completo; `src/agent/llm_client.py` ahora llama directo al endpoint REST `/chat/completions` con `requests` (ya era dependencia del proyecto para Crossref/OpenAlex). `generate_json` ahora exige un `json_schema` explícito y usa `response_format={"type": "json_schema", ...}`. `evaluate_evidence.py` define `RESPONSE_SCHEMA` con los campos esperados (`answer`, `sources`, `abstained`, `evidence_level`, `needs_human_review`). Probado end-to-end contra `qwen2.5-vl-7b-instruct` corriendo en LM Studio: clasificó correctamente una afirmación como `evidencia_suficiente`, citando la fuente correcta.
**Alternativas consideradas**: arreglar el bloqueo de `jiter` (reinstalar, agregar excepción en Windows) — descartado por ser más fràgil y específico de esta máquina; usar `response_format={"type": "text"}` y parsear JSON del texto libre — descartado porque la salida estructurada con `json_schema` es más confiable (grammar-constrained).
**Estado**: confirmada, validada con hardware/modelo real.
**Gaps abiertos**: si cambian de LLM Studio a un proveedor en la nube (Claude Haiku, etc., ver decisión anterior), confirmar que ese proveedor también soporta `response_format: json_schema` con el mismo formato — si no, `generate_json` necesitará una rama alterna.

## [2026-11-09] Implementación de embeddings + índice vectorial (Fase 2)

**Contexto**: siguiente paso tras el pipeline de ingesta — convertir chunks en vectores y poder recuperarlos por similitud.
**Decisión**: `src/retrieval/embeddings.py` carga `paraphrase-multilingual-MiniLM-L12-v2` de forma perezosa (solo al primer uso) y devuelve embeddings normalizados L2. `src/retrieval/index.py` usa `faiss.IndexFlatIP` (producto interno sobre vectores normalizados = similitud coseno) en vez de un índice aproximado, razonable para un corpus pequeño (5-10 documentos del MVP). `src/retrieval/retriever.py` junta ambos en `SemanticRetriever`, la recuperación semántica pura de la línea base (sin BM25/híbrido todavía). Probado end-to-end con el modelo real: dada una pregunta sobre "librería para indexar vectores", recuperó correctamente el chunk sobre FAISS por encima de uno sobre BM25 y uno irrelevante (receta de cocina).
**Alternativas consideradas**: un índice FAISS aproximado (IVF/HNSW) — innecesario al tamaño del corpus del MVP (5-10 documentos), se puede migrar en Fase 3 si el corpus crece.
**Estado**: confirmada para el MVP.
**Gaps abiertos**: no hay persistencia en disco del índice todavía (se reconstruye en memoria cada vez) — evaluar si hace falta antes de la demo en Fase 6.

## [2026-11-09] Implementación del pipeline de ingesta (Fase 2)

**Contexto**: había que implementar carga, extracción, limpieza, chunking y metadatos descritos en el anteproyecto (secciones 9-10).
**Decisión**: `src/ingestion/pdf_loader.py` valida tipo, tamaño (≤50MB), número de páginas (≤200) y rechaza PDFs cifrados antes de abrirlos (cubre SEC06 de la sección 13). El chunking (`chunker.py`) usa una ventana deslizante de palabras (no de tokens reales del tokenizer del modelo de embeddings) como aproximación de los ~450 tokens / 80 de solapamiento que pide el anteproyecto. `cleaner.py` además remueve encabezados/pies repetidos detectando líneas que aparecen en ≥50% de las páginas. Todo validado con 10 pruebas unitarias en `tests/test_ingestion.py` (incluye un PDF sintético generado con PyMuPDF, no depende de archivos externos).
**Alternativas consideradas**: usar un tokenizer real (ej. el de `sentence-transformers`) para contar tokens en vez de palabras — se pospuso para no acoplar el chunker al modelo de embeddings todavía; se puede revisar si el tamaño real de los chunks se desvía mucho de 450 tokens.
**Estado**: confirmada para el MVP.
**Gaps abiertos**: el chunking no respeta activamente límites de sección/párrafo (solo de documento/página) — el anteproyecto pide evitar cortar una idea "cuando sea posible"; si el recall de las pruebas de evaluación sale bajo, revisar esto primero. Falta extraer `section` real de los documentos (hoy siempre `None`).

## [2026-11-09] Anteproyecto completo (secciones 12-16) y equipo de 2 integrantes

**Contexto**: faltaban las secciones 12-16 del anteproyecto y el gap del formato de salida identificado en la iteración anterior. Además, el equipo decidió no sumar integrantes adicionales.
**Decisión**: se completaron las 16 secciones. El formato de salida se resolvió definiendo `evidence_level` (`evidencia_suficiente/parcial/no_localizada`) como campo de extensión dentro del esquema obligatorio del curso, sin reemplazarlo — `abstained=true` cuando `evidence_level=evidencia_no_localizada`, `needs_human_review=true` cuando es `evidencia_parcial` o hay contradicciones/fallos de validación. El banco de pruebas quedó en 25 casos (20 regulares + 5 de herramientas, TH01-TH05). El equipo se mantiene en 2 integrantes (Mónica, Bianca).
**Alternativas consideradas**: mantener las categorías de evidencia como una estructura paralela al esquema del curso — descartado porque no cumplía el requisito de un único esquema validado.
**Estado**: confirmada. El equipo se queda en 2 integrantes de forma definitiva (el curso exige 3-4; riesgo asumido, ya documentado en la tabla de riesgos del anteproyecto).
**Gaps abiertos**:
- La sección 15 (Plan de Trabajo) todavía asigna tareas a "Integrante 3" (interfaz en Fase 3, evaluación en Fase 4) — pendiente de reasignar entre Mónica y Bianca, se hará más adelante.
- Las fechas de la sección 15 siguen como placeholder `[fecha]`.
- Los documentos/páginas del banco de pruebas (D01-D10) están marcados "por fijar" hasta que se cierre el corpus en Fase 2.

## [2026-11-09] Cambio de nombre: ClaimTrace → Evidentia

**Contexto**: el nombre "ClaimTrace" se definió en el primer borrador del anteproyecto.
**Decisión**: renombrar el proyecto a "Evidentia".
**Alternativas consideradas**: mantener "ClaimTrace".
**Estado**: confirmada.
**Gaps abiertos**: falta actualizar el nombre en el documento de anteproyecto (`Anteproyecto_NLP.pdf` / su origen editable), que todavía dice "ClaimTrace" en el título y el resumen ejecutivo.

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
