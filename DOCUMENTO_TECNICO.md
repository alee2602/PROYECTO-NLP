# Evidentia — Documento Técnico Final

Proyecto final, CC3103 Procesamiento de Lenguaje Natural, UVG.
Mónica Salvatierra (22249) · Bianca Calderón (22272)

> Nota de alcance: este documento resume el sistema construido, cómo se
> evaluó y qué limitaciones quedan abiertas. Las decisiones de diseño con su
> razonamiento completo (qué se intentó, qué falló y por qué) están en
> `DECISIONS.md`; aquí solo se citan las que importan para entender el
> resultado final.

## 1. Resumen ejecutivo

Evidentia es un sistema de NLP/RAG agéntico que verifica si afirmaciones
extraídas de documentos académicos tienen respaldo real en un corpus de
fuentes autorizadas. Dado un documento o una afirmación suelta, el sistema:
extrae afirmaciones verificables, recupera evidencia relevante mediante
búsqueda híbrida (semántica + léxica), evalúa esa evidencia con un LLM, y
aplica una capa de verificación determinística (no delegada al LLM) antes
de reportar el resultado — con abstención obligatoria cuando no hay
evidencia suficiente.

El sistema está completo en las 5 primeras fases del curso: ingesta,
recuperación, orquestación agéntica, evaluación con banco de pruebas real,
y seguridad (7 controles adversarios verificados contra el sistema real).
Incluye una interfaz Streamlit funcional para subir documentos y verificar
afirmaciones.

## 2. Problema y motivación

Verificar manualmente si una afirmación en un documento académico está
realmente respaldada por sus fuentes es lento y propenso a error humano —
sobre todo cuando el documento cita decenas de referencias y el lector no
puede releer cada una. Evidentia automatiza esa verificación, pero con una
decisión de diseño central: **nunca confiar en que el LLM "diga la verdad"
por sí solo**. Cada afirmación que el LLM clasifica como respaldada pasa
por un chequeo de código determinístico antes de aceptarse — la cita debe
corresponder a un chunk realmente recuperado, las cifras mencionadas deben
aparecer literalmente en el texto citado, y cualquier patrón de intento de
manipulación (afirmación o documento) fuerza revisión humana sin importar
qué haya respondido el modelo.

Esta decisión viene de evidencia empírica, no de precaución abstracta: en
las primeras pruebas manuales, el LLM validó una cifra inventada ("45% de
mejora") como `evidencia_suficiente` citando un chunk que ni la
mencionaba, y clasificó una afirmación que invertía un hallazgo real como
respaldada en vez de contradicha. Ambos casos se arreglaron con código
determinístico, no con más instrucciones de prompt — ese patrón se repite
en todo el proyecto (ver sección 5).

## 3. Arquitectura

```
Documento/afirmación
      │
      ▼
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐
│extract_claims│───▶│  HybridRetriever  │───▶│  evaluate_claim    │
│ (LLM + filtro│     │ (semántico 70% +  │     │ (LLM + 3 vetos     │
│  de vaguedad │     │  léxico BM25 30%  │     │  determinísticos:  │
│ determinista)│     │  + boost de       │     │  validate_citations│
└─────────────┘     │  identificadores) │     │  check_injection    │
                     └──────────────────┘     │  check_contradiction│
                                               └───────────────────┘
                                                        │
                                                        ▼
                                              EvidentiaOutput
                                   (answer, sources, abstained,
                                    needs_human_review, evidence_level)
```

Orquestado con **LangGraph**: `extract → search → evaluate → (refinar
búsqueda una vez si no hay evidencia) → finalize`, con un tope duro de 3
iteraciones por afirmación y 120 llamadas al LLM por corrida completa
(`src/security/budget.py`) — si se agota el presupuesto, se devuelven los
resultados ya evaluados en vez de fallar toda la corrida.

### 3.1 Ingesta (`src/ingestion/`)

PDF → validación (tipo, tamaño ≤50MB, ≤200 páginas, sin cifrado, sin
JavaScript embebido) → extracción de texto por página (filtrando texto
invisible) → limpieza (de-hyphenation, normalización de ligaduras,
remoción de encabezados/pies repetidos) → chunking (ventana de ~450
palabras, solapamiento 80) → metadata Pydantic por documento y por chunk.

### 3.2 Recuperación (`src/retrieval/`)

Híbrida: embeddings con `paraphrase-multilingual-MiniLM-L12-v2` sobre
FAISS (`IndexFlatIP`) + BM25 propio (sin dependencia externa) + boost de
identificadores técnicos exactos (ej. "BM25", "RAGAS") — necesario porque
las consultas están en español y el corpus en inglés, donde el semántico
solo pierde términos técnicos exactos. Pesos 70% semántico / 30% léxico
(anteproyecto sección 10). Filtro de acceso por `owner_id` para documentos
subidos por un usuario (sección 5.3).

### 3.3 Evaluación de evidencia (`src/agent/evaluate_evidence.py`)

El LLM clasifica la relación afirmación↔evidencia en 3 niveles
(`evidencia_suficiente` / `evidencia_parcial` / `evidencia_no_localizada`),
pero el resultado pasa por 3 vetos de código antes de aceptarse:

- **`validate_citations`**: rechaza citas a chunks no recuperados; degrada
  a parcial si una cifra de la afirmación no aparece literalmente en el
  texto citado (excluyendo identificadores de referencia como IDs de
  arXiv, que no son datos factuales).
- **`check_injection`**: si la afirmación o algún fragmento de evidencia
  contiene un patrón de manipulación de instrucciones, degrada a revisión
  humana sin importar qué haya respondido el modelo (sección 5.1-5.2).
- **`check_contradiction`**: veto adicional vía una segunda llamada al LLM
  especializada en detectar contradicción directa.

### 3.4 Esquema de salida

`EvidentiaOutput` (Pydantic): `answer`, `sources`, `abstained`,
`tool_used`, `needs_human_review`, más `evidence_level`/`claim`/`claim_id`
como extensión propia. Invariantes de consistencia reforzadas en el
esquema mismo, no solo por instrucción de prompt: `abstained=True` exige
`sources=[]`, `evidence_level=no_localizada` **y**
`needs_human_review=True` (una abstención debe detenerse y pedir
confirmación humana, nunca quedar silenciosa).

### 3.5 Interfaz (`app/`)

Streamlit: subir un PDF (validado, con `owner_id` de sesión) o elegir un
documento del corpus, analizar sus afirmaciones o verificar una afirmación
suelta. Resumen por nivel de evidencia, fuentes con el fragmento citado,
JSON de salida completo.

## 4. Metodología de evaluación (Fase 4)

Banco de 25 casos (`data/eval/test_cases.json`, TC01-TC20 + TH01-TH05)
diseñado en el anteproyecto (sección 12), con afirmaciones reales
verificadas manualmente contra el corpus (no genéricas) — cubre afirmación
directa, paráfrasis, paráfrasis multilingüe, contradicción, identificador
léxico exacto, afirmación compuesta (multi-documento), afirmación
ambigua/vaga, ausencia total de evidencia, vigencia de versión/fecha, y
selección/degradación de herramienta.

**Corpus**: 20 documentos de arXiv (D01-D10 núcleo + D11-D20 distractores
temáticamente adversariales), 472 chunks.

**Métricas**: Recall@5 (documento esperado recuperado en el top-5),
MRR, exactitud de clasificación (`evidence_level` exacto == esperado),
latencia (media/P95) y tokens/llamadas al LLM.

**Nota de metodología importante**: Recall@5 exige el conjunto COMPLETO de
documentos esperados para afirmaciones compuestas (categoría distinta de
"ambigua", donde varias fuentes alternativas son igualmente válidas) — no
basta con recuperar uno de dos documentos necesarios. Este ajuste se hizo
después de notar que la métrica original (overlap "any") ocultaba un hueco
real de recuperación en un caso compuesto (TC14): ver `DECISIONS.md`.

**Verificación de que el Recall@5 no es un artefacto**: ablation de
recuperación (`scripts/run_retrieval_ablation.py`) comparando
solo-semántico / solo-léxico / híbrido-sin-boost / híbrido-completo, y
repetida con el corpus duplicado a 20 documentos con distractores reales —
el resultado se sostiene igual, el boost de identificadores solo rescata
un caso específico (no está "cargando" el número).

## 5. Seguridad (Fase 5)

Los 7 casos adversarios del anteproyecto (sección 13) están implementados
y verificados contra el sistema real (corpus completo + LM Studio), no
solo en tests unitarios con clientes simulados — `scripts/run_security_eval.py`.

| ID | Amenaza | Mitigación | Resultado observado |
|---|---|---|---|
| SEC01 | Inyección directa en la consulta | Detector de patrones (regex ES/EN) + separación de roles explícita en el prompt + veto determinístico post-LLM | El LLM real ignoró la instrucción incrustada; clasificación basada solo en evidencia |
| SEC02 | Inyección indirecta (texto oculto en PDF) | Filtro de texto invisible en extracción (tamaño de fuente casi nulo o blanco sobre blanco) + mismo veto de SEC01 sobre los fragmentos | Texto oculto filtrado antes de llegar al chunk; cero regresión en los 20 documentos reales |
| SEC03 | Evasión de permisos (fragmento de otro usuario) | Filtro `owner_id` aplicado antes de recortar el pool de candidatos; sin identidad, solo se ven chunks públicos | Chunk ajeno nunca devuelto, incluso siendo mejor candidato léxico/semántico |
| SEC04 | Acción crítica sin autorización (ampliar búsqueda / llamada externa) | Tope estructural de iteraciones del agente (3) + presupuesto de llamadas LLM (120) + lista blanca de dominios externos | Máximo 2 búsquedas por afirmación; dominio no permitido rechazado antes de conectar |
| SEC05 | Alucinación forzada (autor/página ausente) | `validate_citations` (rechaza citas a chunks no recuperados) + regla de esquema (abstención ⇒ revisión humana obligatoria) | Abstención limpia, sin inventar cita ni página |
| SEC06 | Archivo malicioso o inválido | Validación de tipo MIME/extensión, tamaño, páginas, cifrado, JavaScript embebido (vía sintaxis de objetos PDF, no bytes crudos) | Los 3 tipos de archivo malicioso rechazados; 20/20 documentos reales cargan sin falsos positivos |
| SEC07 | Fuga de datos personales en logs | Sanitización por regex (correos/teléfonos) + registro de hash en vez de texto completo | El log no contiene ni el correo ni el teléfono de prueba, solo un hash |

**Hallazgos colaterales durante la implementación de seguridad** (honestos,
no ocultados): se encontró y corrigió un bug preexistente real en
`pdf_loader.py` (cerraba el documento antes de leer `page_count` en el
mensaje de error); un primer intento de detección de JavaScript por bytes
crudos daba falsos positivos reales en 2 de los 20 documentos del corpus
(contenido binario comprimido coincidiendo por azar con el patrón "/JS");
y un bug real en el filtro `owner_id` (se aplicaba después de recortar el
pool de candidatos, dejando sin resultados al dueño legítimo cuando chunks
ajenos rankeaban mejor) — corregido por el equipo.

**Decisión de diseño reciente**: `owner_id=None` (sin identidad) ahora
oculta todos los chunks privados por defecto — antes desactivaba el
filtro por completo. Cero regresión en el corpus compartido (todo público
por defecto); cierra un hueco real ahora que la interfaz expone subida de
PDFs.

**Gap documentado**: la mitigación de SEC07 pide "regex + spaCy NER"; spaCy
quedó bloqueado por el Control de aplicaciones de Windows en este entorno
de desarrollo (igual que `torch` y el SDK de `openai` antes) — la
sanitización por regex (correos, teléfonos) está implementada y
verificada; la detección de nombres propios sin NER queda como mejora
pendiente.

## 6. Resultados

Corrida completa contra el sistema real (corpus de 20 documentos / 472
chunks, `qwen/qwen3.5-9b`, contexto 16384), 23 casos de contenido + 2
casos de robustez de parámetros (TH03/TH04):

| Métrica | Valor |
|---|---|
| Recall@5 | **95.24% (20/21)** |
| MRR | **0.921** |
| Exactitud de clasificación | **91.30% (21/23)** |
| TH03 (límite duro `top_k≤20`) | Cumple |
| Latencia de búsqueda | media 0.119s, P95 0.494s |
| Latencia de `evaluate_claim` | media 94.6s*, P95 48.3s |
| Llamadas al LLM / tokens totales | 52 llamadas, 165,864 tokens |

\* La media de latencia de `evaluate_claim` está inflada por un caso
(TC09) que tardó 1609s (27 min) de forma anómala — el resto de los 22
casos tardó entre 15s y 50s. Se reporta el dato completo sin descartar el
outlier porque es información operativa real (el peor caso observado
puede ser mucho peor que el P95), consistente con una degradación ya
documentada del motor de inferencia local.

**Los 2 casos que no coinciden** (TC14, TC15) son limitaciones reales y
ya conocidas, no errores de calibración del banco de pruebas (ver sección
7) — se revisó explícitamente si ajustar las etiquetas esperadas de
`test_cases.json` resolvería esto, y se decidió no hacerlo: hubiera sido
maquillar el número, no arreglar nada.

**Verificación de que el Recall@5 no es un artefacto**: ablation de
recuperación (solo-semántico / solo-léxico / híbrido-sin-boost /
híbrido-completo) repetida con el corpus duplicado a 20 documentos — el
resultado se sostiene, el boost de identificadores solo rescata 1 caso
específico.

**Comparación línea base (Fase 2) vs. mejorada (Fase 3)**: mismo banco,
mismo pipeline de `evaluate_claim`, solo cambia el retriever
(`scripts/run_baseline_vs_improved.py`):

| Métrica | Línea base (solo semántico) | Mejorada (híbrido) |
|---|---|---|
| Recall@5 | 85.7% | 95.2% |
| MRR | 0.720 | 0.921 |
| Exactitud de clasificación | **65.2%** | **91.3%** |

6 casos cambian de clasificación entre variantes (TC10, TC11, TC12, TC13,
TC19, TH02) — en los 6, la mejora de recuperación es lo que permite que
`evaluate_claim` llegue a la clasificación correcta. Esta es la evidencia
concreta de que la mejora técnica de Fase 3 (BM25 propio + boost de
identificadores) no es una mejora de recuperación aislada: se traduce
directamente en **+26 puntos porcentuales** de exactitud de clasificación
final, que es la métrica que de verdad le importa al usuario.

## 7. Limitaciones conocidas

- **Contradicción cruzada entre documentos lejanamente relacionados**:
  cuando dos papers no relacionados contienen afirmaciones genéricas
  similares ("nuestro método mejora el rendimiento"), el modelo puede
  combinarlas para respaldar una afirmación deliberadamente vaga que
  debería quedar como evidencia parcial. Se intentó un arreglo de prompt
  que causó una regresión neta en otros casos y se revirtió — sigue
  abierto como limitación de robustez ante vaguedad, no como error de
  calibración del banco de pruebas.
- **Recuperación de afirmaciones compuestas entre documentos no
  relacionados**: el orquestador solo reintenta la búsqueda cuando el
  resultado es "evidencia no localizada", no cuando ya hay evidencia
  parcial para una parte de una afirmación compuesta — un documento
  esperado puede no recuperarse nunca si el otro domina el top-5.
- **No-determinismo residual del motor de inferencia local**: con
  `temperature=0.0`, corridas idénticas de código pueden dar conjuntos de
  casos fallidos ligeramente distintos (confirmado empíricamente,
  documentado en `DECISIONS.md`) — el total se mantiene en un rango
  estable, pero el caso exacto que falla puede variar.
- **spaCy NER bloqueado** en el entorno de desarrollo Windows (ver sección
  5) — sanitización de logs hoy es solo por regex.
- **Chunking por palabras, no por tokens reales** del tokenizer del
  modelo de embeddings — aproximación documentada, no exacta.

## 8. Conclusiones

El patrón más importante de todo el proyecto: **cuando el LLM falla, la
solución real casi nunca fue "ajustar el prompt" — fue escribir un
chequeo determinístico que no depende de que el modelo se comporte bien.**
Esto se repitió en citas numéricas inventadas, en contradicciones, en
intentos de inyección, y en archivos maliciosos. El prompt engineering
tuvo rendimientos decrecientes claros y, en al menos un caso documentado,
produjo una regresión neta que hubo que revertir.

El segundo patrón: **nunca declarar un arreglo resuelto sin verificarlo
contra el sistema real** (corpus real + LLM real, no solo tests con
clientes simulados) — varias correcciones que parecían funcionar en
aislamiento resultaron insuficientes o regresivas solo al confirmarse así.

## Referencias

Ver `DECISIONS.md` para el registro completo de decisiones de diseño,
iteraciones fallidas y su razonamiento. Corpus construido desde la API
pública de arXiv (`scripts/build_corpus.py`); metadatos bibliográficos
contrastados vía Crossref.
