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

## [2026-11-10] Primera corrida real del banco de pruebas (Fase 4): Recall@5=100%, exactitud de clasificación=30% (con matices importantes)

**Contexto**: el banco de pruebas de 25 casos del anteproyecto (sección 12) estaba escrito de forma genérica, sin afirmaciones concretas, porque se diseñó antes de tener el corpus real. Se redactaron 25 afirmaciones genuinas basadas en contenido verificado de D01-D10 (`data/eval/test_cases.json`) y se construyó `scripts/run_eval.py` para correrlas contra el sistema real y calcular métricas, en vez de seguir midiendo con ejemplos sueltos.

**Resultado crudo**: Recall@5 = 100% (21/21 — el documento esperado siempre apareció en el top-5). Exactitud de clasificación (evidence_level exacto == esperado) = 30.4% (7/23). El número de clasificación por sí solo es engañoso; desglose real tras leer las 23 respuestas completas (no solo la etiqueta):

- **3/23 (TC01, TC03, TC14) son fallas de generación del motor** ("No fue posible generar una evaluación válida"), no errores de razonamiento — mismo bug de llama.cpp/LM Studio ya documentado (grammar-constrained decoding). El sistema se abstiene de forma segura, como está diseñado. Cuentan como "fallo" en la métrica estricta pero no son un defecto de clasificación.
- **~13/23 son el modelo siendo MÁS CONSERVADOR de lo que predije** (p. ej. clasifica "evidencia_parcial" o "evidencia_no_localizada" donde yo esperaba "evidencia_suficiente"), pero citando el documento correcto y con razonamiento sólido en el campo `answer`. Ejemplos concretos inspeccionados: TC06 identificó la paráfrasis completa correctamente pero la etiquetó "parcial"; TC13 y TC16 **detectaron correctamente** que la afirmación decía más de lo que el fragmento respalda (justo el matiz que buscaban esos casos) pero usaron una categoría más severa ("no_localizada") de la que yo anticipé ("parcial"). Es una diferencia de calibración/umbral, no un error de fondo — y es la dirección seguridad-primero (subconfianza, no sobreconfianza).
- **1/23 (TC08) es una falla real y confirmada, no solo de calibración**: la afirmación decía que los sistemas automatizados NO reducen el tiempo/esfuerzo (falso, invierte un hallazgo de D02). El modelo escribió en su propia respuesta el hecho correcto que CONTRADICE la afirmación ("...SÍ pueden reducir el tiempo...") pero aun así clasificó `evidencia_suficiente`. **Esto confirma que el arreglo de contradicción de la entrada anterior (`SYSTEM_PROMPT` con regla + ejemplo few-shot) no generaliza a redacciones nuevas de contradicción** — sigue siendo un riesgo real, no resuelto de raíz.
- **1/23 (TC17) se salvó por suerte, no por diseño**: la afirmación era sobre un tema totalmente ausente del corpus (traducción automática/WMT14). El modelo no reconoció limpiamente la ausencia total del tema y citó D09 (RAGAS) de forma tangencial; `validate_citations` lo degradó de categoría solo porque la cifra "14" (de "WMT14") no aparecía literalmente en el chunk citado — una coincidencia afortunada del chequeo numérico, no una detección real de "tema fuera de alcance".

**Decisión**: no seguir parchando el prompt de `evaluate_evidence` por ahora — ya se intentó dos veces (contradicción, vaguedad) con éxito parcial y claros rendimientos decrecientes. Se documenta esto como limitación conocida y medida del sistema (útil directamente para la sección "limitaciones operativas" del documento técnico final, que el curso pide explícitamente). Los 25 casos y el runner quedan reutilizables para volver a medir si se cambia de modelo (ej. una API en la nube) o se ajusta el prompt más adelante.

**Hallazgo adicional (TH03)**: el sistema NO aplica el límite duro `top_k ≤ 20` que pide el anteproyecto (sección 11: "se aplican los límites... top_k ≤ 20, max_claims ≤ 15") — con `top_k=500` el sistema devolvió 40 resultados (limitado solo por el tamaño real del corpus, no por una validación explícita). Esto es un gap real de validación de parámetros, no implementado todavía.

**Estado**: medición confirmada con 23 casos reales corridos contra el sistema completo (recuperación + LLM real + validate_citations). Gap de contradicción (TC08) y de reconocimiento de ausencia total de tema (TC17) quedan documentados como limitaciones abiertas para la sección de seguridad/limitaciones del documento técnico.
**Gaps abiertos**:
- Contradicción (TC08): necesitaría un modelo más grande o una estrategia distinta (ej. un paso de verificación separado) para resolverse de raíz, no solo prompt engineering.
- Reconocimiento de "tema totalmente fuera del corpus" (TC17): el modelo no lo detecta de forma confiable por sí mismo.
- Validación de límites de parámetros (top_k≤20, max_claims≤15) de la sección 11 del anteproyecto: no implementada.
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
