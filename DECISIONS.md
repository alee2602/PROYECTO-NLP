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
