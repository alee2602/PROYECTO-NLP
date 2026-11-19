# Evidentia

## Documento técnico final

Proyecto final del curso CC3103, Procesamiento de Lenguaje Natural, Universidad del Valle de Guatemala.

Mónica Salvatierra (22249) y Bianca Calderón (22272).

Este documento resume el sistema construido, la forma en que se evaluó y las limitaciones que todavía quedan abiertas. Las decisiones de diseño con su razonamiento completo, incluyendo qué se intentó, qué no funcionó y por qué, están documentadas en `DECISIONS.md`. Aquí solo se citan las decisiones necesarias para entender el resultado final. El plan de trabajo con fechas y responsables reales se encuentra en `PLAN_DE_TRABAJO.md`.

El código, las pruebas automatizadas y el registro completo de decisiones están disponibles en el repositorio del equipo, cuyo archivo `README.md` describe las instrucciones de instalación y ejecución. El corpus y el material propio del curso no se versionan en el repositorio, por los motivos que se explican en la sección 3.1.

## 1. Resumen ejecutivo

Evidentia es un sistema agéntico de procesamiento de lenguaje natural y recuperación aumentada de información cuyo propósito es verificar si las afirmaciones extraídas de documentos académicos tienen respaldo real dentro de un corpus de fuentes autorizadas. Dado un documento completo o una afirmación suelta, el sistema extrae las afirmaciones verificables que contiene, recupera evidencia relevante mediante una búsqueda híbrida que combina recuperación semántica y léxica, evalúa esa evidencia con un modelo de lenguaje y, por último, aplica una capa de verificación determinística que no depende del modelo antes de entregar un resultado. Cuando no existe evidencia suficiente, el sistema se abstiene de forma obligatoria en lugar de inventar una respuesta.

El proyecto está completo en las primeras cinco fases del curso. Esto incluye la ingesta de documentos, la recuperación de evidencia, la orquestación agéntica, la evaluación mediante un banco de pruebas real y la seguridad, con siete controles adversarios verificados contra el sistema en funcionamiento. El sistema cuenta además con una interfaz construida en Streamlit que permite subir documentos y verificar afirmaciones de forma interactiva.

## 2. Problema y motivación

Verificar a mano si una afirmación dentro de un documento académico está realmente respaldada por sus fuentes es una tarea lenta y propensa al error humano, sobre todo cuando el documento cita decenas de referencias y no hay tiempo de releer cada una con cuidado. Evidentia automatiza esa verificación, pero parte de una decisión de diseño central. El sistema nunca confía en que el modelo de lenguaje diga la verdad por sí solo. Toda afirmación que el modelo clasifica como respaldada pasa antes por un chequeo de código determinístico. Ese chequeo exige que la cita corresponda a un fragmento realmente recuperado, que las cifras mencionadas en la afirmación aparezcan de forma literal en el texto citado y que cualquier patrón de intento de manipulación, ya sea en la afirmación o en el propio documento, obligue a una revisión humana sin importar lo que haya respondido el modelo.

Esta decisión surgió de evidencia empírica y no de una precaución abstracta. En las primeras pruebas manuales del sistema, el modelo validó una cifra inventada, un supuesto cuarenta y cinco por ciento de mejora, como evidencia suficiente, citando un fragmento que ni siquiera mencionaba esa cifra. En otra prueba, el modelo clasificó como respaldada una afirmación que en realidad invertía un hallazgo real del documento citado, cuando debía clasificarse como contradicha. Ambos problemas se resolvieron escribiendo código determinístico, no agregando más instrucciones al mensaje del sistema. Ese mismo patrón se repite a lo largo de todo el proyecto y se retoma en la sección cinco.

## 3. Arquitectura

El flujo del sistema parte de un documento o una afirmación suelta. Primero, el componente de extracción de afirmaciones identifica qué partes del texto son afirmaciones verificables, apoyándose en el modelo de lenguaje y en un filtro determinístico que descarta afirmaciones demasiado vagas. Después, el recuperador híbrido busca evidencia relevante combinando un setenta por ciento de peso semántico con un treinta por ciento de peso léxico, más un refuerzo adicional para identificadores técnicos exactos. Finalmente, el componente de evaluación de evidencia pide al modelo que clasifique la relación entre la afirmación y la evidencia recuperada, y pasa ese resultado por tres verificaciones determinísticas antes de aceptarlo. La salida final es un objeto `EvidentiaOutput` que incluye la respuesta, las fuentes citadas, si el sistema se abstuvo, si la afirmación necesita revisión humana y el nivel de evidencia asignado.

Todo el flujo está orquestado con LangGraph siguiendo la secuencia de extraer afirmaciones, buscar evidencia, evaluarla, refinar la búsqueda una sola vez si no se encontró evidencia, y finalizar. Existe además un tope duro de tres iteraciones de refinamiento por afirmación y un presupuesto máximo de ciento veinte llamadas al modelo por corrida completa, definidos en `src/security/budget.py`. Si ese presupuesto se agota, el sistema devuelve los resultados que ya había evaluado en lugar de hacer fallar toda la corrida.

### 3.1 Ingesta de documentos

El flujo de ingesta, implementado en `src/ingestion/`, parte de un archivo PDF que se valida por tipo, tamaño máximo de cincuenta megabytes, máximo de doscientas páginas, ausencia de cifrado y ausencia de JavaScript embebido. Luego se extrae el texto de cada página, filtrando cualquier texto invisible que pudiera estar oculto. El texto se limpia quitando guiones de corte de línea, normalizando ligaduras tipográficas y eliminando encabezados y pies de página repetidos. Por último, el texto se segmenta en fragmentos de alrededor de cuatrocientas cincuenta palabras con un solapamiento de ochenta palabras entre fragmentos consecutivos, y a cada documento y cada fragmento se les asigna metadata validada con Pydantic.

El corpus del proyecto está compuesto por veinte artículos públicos de arXiv, diez que forman el núcleo original del corpus y diez más que funcionan como distractores temáticos. Todos se descargaron mediante la API pública de arXiv, usando el script `scripts/build_corpus.py`, y cada documento conserva registrada su licencia dentro de su metadata.

Ni los PDFs originales, guardados en `data/raw/`, ni el texto completo extraído en `data/processed/chunks.jsonl`, se versionan en el repositorio, porque el contenido de artículos de terceros no debe redistribuirse por ese medio. Lo único que se versiona es `documents.json`, que contiene únicamente metadata bibliográfica como el título, los autores, la fuente y la licencia. Cualquier persona que clone el repositorio puede regenerar el corpus completo corriendo `python scripts/build_corpus.py`, siempre que tenga conexión a internet.

El proyecto está construido en Python 3.12 y usa, entre otras, las siguientes bibliotecas. PyMuPDF para la extracción de texto de los PDFs, Sentence Transformers junto con FAISS para los embeddings y el índice vectorial, una implementación propia de BM25 sin dependencias externas, LangGraph para la orquestación agéntica, Pydantic para los esquemas y su validación, Streamlit para la interfaz y pytest para las ciento veintidós pruebas automatizadas del proyecto. El cliente del modelo de lenguaje se construyó directamente sobre la biblioteca `requests`, hablando el protocolo REST sin usar el SDK oficial de OpenAI, de modo que es compatible tanto con LM Studio corriendo localmente como con cualquier proveedor que hable ese mismo protocolo.

### 3.2 Recuperación de evidencia

La recuperación de evidencia, implementada en `src/retrieval/`, es híbrida. Combina embeddings generados con el modelo `paraphrase-multilingual-MiniLM-L12-v2` sobre un índice FAISS de tipo `IndexFlatIP`, una implementación propia de BM25 sin dependencias externas, y un refuerzo adicional para identificadores técnicos exactos como "BM25" o "RAGAS". Este refuerzo resultó necesario porque las consultas están escritas en español mientras que el corpus está en inglés, y la búsqueda puramente semántica tiende a perder justamente los términos técnicos exactos que sí aparecen de forma literal en el texto. Los pesos usados son setenta por ciento para la componente semántica y treinta por ciento para la componente léxica. La recuperación también respeta un filtro de acceso basado en la identidad de quien sube un documento, descrito en el control SEC03 de la sección cinco.

### 3.3 Evaluación de evidencia

El componente de evaluación de evidencia, implementado en `src/agent/evaluate_evidence.py`, pide al modelo de lenguaje que clasifique la relación entre una afirmación y la evidencia recuperada en tres niveles posibles, evidencia suficiente, evidencia parcial o evidencia no localizada. Antes de aceptar esa clasificación, el resultado pasa por tres verificaciones de código independientes del modelo.

La primera, `validate_citations`, rechaza cualquier cita que apunte a un fragmento que en realidad no fue recuperado, y degrada la clasificación a parcial si la afirmación menciona una cifra específica que no aparece de forma literal en el texto citado, descontando identificadores de referencia como los códigos de arXiv, que no son datos factuales sino simples etiquetas. La segunda, `check_injection`, revisa si la afirmación o algún fragmento de evidencia contiene un patrón de manipulación de instrucciones, y de ser así degrada el resultado a revisión humana sin importar lo que haya respondido el modelo, como se detalla en los controles SEC01 y SEC02 de la sección cinco. La tercera, `check_contradiction`, es un veto adicional que usa una segunda llamada al modelo especializada en detectar contradicción directa entre la afirmación y la evidencia.

El esquema de salida `EvidentiaOutput`, construido con Pydantic, incluye los campos `answer`, `sources`, `abstained`, `tool_used` y `needs_human_review`, además de `evidence_level`, `claim` y `claim_id` como extensión propia del proyecto. Las reglas de consistencia quedan reforzadas dentro del propio esquema y no dependen únicamente de la instrucción dada al modelo. En particular, si el sistema se abstiene, el esquema exige que las fuentes estén vacías, que el nivel de evidencia sea no localizada y que el campo de revisión humana quede en verdadero, de modo que una abstención siempre se detenga a pedir confirmación humana y nunca quede silenciosa.

Un ejemplo real de salida, correspondiente al caso de prueba TC01, con evidencia suficiente, es el siguiente.

```json
{
  "answer": "El fragmento D01_0002 confirma que los vectores recuperados se integran en el modelo para informar la predicción del siguiente parche.",
  "sources": [{"source": "D01", "page": 2, "chunk_id": "D01_0002"}],
  "abstained": false,
  "tool_used": "search_evidence",
  "needs_human_review": false,
  "claim_id": "TC01",
  "claim": "Los vectores recuperados se integran en el modelo para informar y mejorar la predicción del siguiente parche.",
  "evidence_level": "evidencia_suficiente"
}
```

### 3.4 Interfaz

La interfaz, construida con Streamlit en `app/streamlit_app.py`, permite subir un PDF propio, validado y asociado a una identidad de sesión, o bien elegir un documento del corpus ya disponible, para después analizar sus afirmaciones o verificar una afirmación suelta escrita a mano. Muestra un resumen por nivel de evidencia, las fuentes citadas junto con el fragmento correspondiente, y la salida completa en formato JSON.

## 4. Metodología de evaluación

El banco de pruebas oficial, definido en `data/eval/test_cases.json`, está compuesto por veinticinco casos identificados como TC01 a TC20 y TH01 a TH05, diseñados originalmente en la sección doce del anteproyecto. Cada afirmación del banco es real y fue verificada manualmente contra el corpus, en lugar de ser una afirmación genérica. El banco cubre afirmaciones directas, paráfrasis en el mismo idioma y en otro idioma, contradicciones, identificadores léxicos exactos, afirmaciones compuestas que requieren más de un documento, afirmaciones ambiguas o deliberadamente vagas, ausencia total de evidencia, vigencia de versión o fecha de publicación, y selección o degradación de herramientas.

Las métricas usadas para medir el desempeño del sistema son el Recall en los primeros cinco resultados recuperados, la posición media del primer resultado relevante o MRR, la exactitud de clasificación, entendida como la coincidencia exacta entre el nivel de evidencia asignado y el esperado, la latencia de búsqueda y de evaluación, y el número de llamadas y de tokens consumidos por el modelo de lenguaje.

Un aspecto importante de la metodología merece explicarse con cuidado. La métrica de Recall exige recuperar el conjunto completo de documentos esperados en las afirmaciones compuestas, en lugar de conformarse con recuperar al menos uno de ellos. La única excepción es la categoría de afirmaciones ambiguas, donde varias fuentes alternativas resultan igualmente válidas por diseño. Este ajuste se hizo después de notar que la métrica original, que se conformaba con recuperar cualquiera de los documentos esperados, ocultaba un vacío real de recuperación en un caso compuesto específico, documentado como TC14 en `DECISIONS.md`.

Para confirmar que el Recall obtenido no es un artefacto de medición, se realizó un estudio de ablación comparando la recuperación puramente semántica, la puramente léxica, la híbrida sin el refuerzo de identificadores y la híbrida completa, usando el script `scripts/run_retrieval_ablation.py`. El mismo estudio se repitió después de duplicar el corpus a veinte documentos agregando distractores temáticos reales, y el resultado se mantuvo estable. El refuerzo de identificadores solo resulta decisivo en un único caso específico, por lo que no está inflando el número de forma artificial.

## 5. Seguridad

Los siete casos adversarios definidos en la sección trece del anteproyecto están implementados y, lo que es más importante, verificados contra el sistema en funcionamiento, usando el corpus completo y el servidor local de LM Studio, mediante el script `scripts/run_security_eval.py`, y no solamente mediante pruebas unitarias con clientes simulados.

El primer control, SEC01, corresponde a la inyección directa de instrucciones dentro de una consulta. Se mitiga con un detector de patrones en español e inglés, una separación explícita de roles dentro del mensaje al modelo y un veto determinístico posterior a la respuesta del modelo. En la prueba real, el modelo ignoró la instrucción incrustada en la afirmación y clasificó basándose únicamente en la evidencia disponible.

El segundo, SEC02, corresponde a la inyección indirecta mediante texto oculto dentro de un PDF. Se mitiga filtrando, durante la extracción, cualquier texto con un tamaño de fuente casi nulo o del mismo color que el fondo, y aplicando sobre los propios fragmentos de evidencia el mismo veto usado contra SEC01. En la prueba real, el texto oculto quedó filtrado antes de llegar al fragmento final, sin ninguna regresión sobre los veinte documentos reales del corpus.

El tercero, SEC03, corresponde a la evasión de permisos, es decir, a la posibilidad de recuperar un fragmento que pertenece a otro usuario. Se mitiga con un filtro basado en la identidad del propietario del documento, aplicado antes de recortar el conjunto de candidatos, de modo que, sin una identidad explícita, solo se devuelven los fragmentos públicos. En la prueba real, el fragmento ajeno nunca se devolvió, incluso cuando resultaba ser el mejor candidato tanto léxico como semántico.

El cuarto, SEC04, corresponde a una acción crítica sin autorización, como ampliar una búsqueda más allá de lo permitido o realizar una llamada externa indebida. Se mitiga con un tope estructural de tres iteraciones del agente, un presupuesto máximo de llamadas al modelo y una lista blanca de dominios externos permitidos. En la prueba real, el sistema nunca hizo más de dos búsquedas por afirmación, y un dominio no permitido fue rechazado antes de intentar siquiera la conexión.

El quinto, SEC05, corresponde a la alucinación forzada, por ejemplo pedir la página exacta donde un autor inexistente en el corpus habría dicho algo. Se mitiga mediante `validate_citations`, que rechaza cualquier cita a un fragmento no recuperado, y mediante la regla del esquema que obliga a toda abstención a exigir revisión humana. En la prueba real, el sistema se abstuvo de forma limpia, sin inventar ninguna cita ni ninguna página.

El sexto, SEC06, corresponde a archivos maliciosos o inválidos. Se mitiga validando el tipo de archivo, su tamaño, su número de páginas, si está cifrado y si contiene JavaScript embebido, esto último revisando la sintaxis de los objetos internos del PDF en lugar de buscar patrones en los bytes crudos del archivo. En la prueba real, los tres tipos de archivo malicioso probados fueron rechazados correctamente, y los veinte documentos reales del corpus se siguen cargando sin ningún falso positivo.

El séptimo, SEC07, corresponde a la fuga de datos personales dentro de los registros de eventos del sistema. Se mitiga con una sanitización por expresiones regulares que detecta correos electrónicos y números de teléfono, y registrando un resumen criptográfico de la afirmación en lugar de su texto completo. En la prueba real, el registro de eventos no contuvo ni el correo ni el teléfono usados en la afirmación de prueba, solamente su resumen criptográfico.

Durante la implementación de estos controles de seguridad surgieron hallazgos adicionales que conviene documentar con la misma honestidad que el resto del proyecto. Se encontró y corrigió un error real preexistente en `pdf_loader.py`, que cerraba el documento antes de volver a leer el número de páginas dentro del mensaje de error. Un primer intento de detectar JavaScript embebido buscando directamente en los bytes crudos del archivo producía falsos positivos reales en dos de los veinte documentos del corpus, porque contenido binario comprimido coincidía por azar con el patrón buscado, y tuvo que sustituirse por el análisis de la sintaxis de los objetos del PDF. También se encontró y corrigió un error real en el filtro de identidad de propietario, que se aplicaba después de recortar el conjunto de candidatos y por eso podía dejar sin resultados al propietario legítimo cuando fragmentos ajenos rankeaban mejor.

Más recientemente, el equipo decidió que la ausencia de identidad, es decir, cuando no se especifica ningún propietario al hacer una consulta, debe ocultar todos los fragmentos privados en lugar de desactivar el filtro por completo, que era el comportamiento anterior. Este cambio no produce ninguna regresión sobre el corpus compartido actual, porque todos sus fragmentos ya son públicos por defecto, y cierra un vacío real ahora que la interfaz permite subir documentos propios.

Queda un vacío documentado y no oculto en la mitigación del séptimo control. El anteproyecto pide combinar expresiones regulares con reconocimiento de entidades nombradas mediante spaCy, pero esa biblioteca quedó bloqueada por el Control de aplicaciones de Windows en este entorno de desarrollo, de la misma forma en que antes bloqueó a `torch` y al SDK de `openai`. La sanitización por expresiones regulares, que cubre correos y teléfonos, ya está implementada y verificada, mientras que la detección de nombres propios sin ese reconocimiento de entidades queda como una mejora pendiente.

## 6. Resultados

La corrida más reciente contra el sistema real, usando el corpus completo de veinte documentos y cuatrocientos setenta y dos fragmentos, el modelo `qwen/qwen3.5-9b` y un contexto de dieciséis mil trescientos ochenta y cuatro tokens, cubrió los veintitrés casos de contenido del banco de pruebas más los dos casos de robustez de parámetros, TH03 y TH04.

El Recall obtenido fue de noventa y cinco coma veinticuatro por ciento, equivalente a veinte de veintiún casos aplicables. El MRR resultó en cero coma novecientos veintiuno. La exactitud de clasificación llegó a noventa y uno coma treinta por ciento, equivalente a veintiuno de veintitrés casos. El caso TH03 confirmó que el sistema respeta el límite duro de un máximo de veinte resultados por búsqueda. El caso TH04 confirmó que, ante una afirmación sin respaldo real, el sistema jamás fuerza una clasificación de evidencia suficiente y siempre exige revisión humana. La latencia media de búsqueda fue de treinta y tres milisegundos, con un percentil noventa y cinco de cuarenta y seis milisegundos. La latencia media de evaluación de una afirmación completa fue de veintitrés coma seis segundos, con un percentil noventa y cinco de treinta y ocho coma dos segundos. En total, la corrida consumió cincuenta y siete llamadas al modelo de lenguaje y doscientos dos mil seiscientos setenta y seis tokens.

Conviene dejar constancia de un dato operativo observado en una corrida anterior con el mismo código. En esa corrida, un único caso tardó mil seiscientos nueve segundos, unos veintisiete minutos, de forma anómala, mientras que el resto de los casos se comportó de manera similar a la corrida más reciente. Ese dato no se descarta, porque refleja información real sobre el peor caso posible de latencia, aunque no representa el comportamiento típico del sistema.

Los dos casos que no coinciden con lo esperado, TC14 y TC15, corresponden a limitaciones reales y ya conocidas del sistema, no a errores de calibración del banco de pruebas, como se explica con más detalle en la sección siete. El equipo revisó explícitamente si ajustar las etiquetas esperadas en `test_cases.json` resolvería el problema, y decidió no hacerlo, porque eso habría maquillado el número en lugar de arreglar algo real.

La comparación entre la línea base de la fase dos, que usa solamente recuperación semántica, y la versión mejorada de la fase tres, que usa recuperación híbrida, se hizo manteniendo constante el mismo banco de pruebas y el mismo flujo de evaluación, de modo que la única variable que cambia es el recuperador. Los resultados se muestran en la siguiente tabla.

| Métrica | Línea base, solo semántica | Versión mejorada, híbrida |
|---|---|---|
| Recall en los primeros cinco resultados | 85.7 por ciento | 95.2 por ciento |
| MRR | 0.720 | 0.921 |
| Exactitud de clasificación | 65.2 por ciento | 91.3 por ciento |

Seis casos cambian de clasificación entre una variante y la otra, identificados como TC10, TC11, TC12, TC13, TC19 y TH02. En los seis, es precisamente la mejora en la recuperación la que permite que la evaluación de evidencia llegue a la clasificación correcta. Esta tabla constituye la evidencia concreta de que la mejora técnica de la fase tres no es una mejora de recuperación aislada, sino que se traduce directamente en veintiséis puntos porcentuales de mejora en la exactitud de clasificación final, que es la métrica que de verdad le importa a quien usa el sistema.

## 7. Limitaciones conocidas

El sistema presenta una limitación de robustez ante afirmaciones deliberadamente vagas que combinan contenido de documentos lejanamente relacionados. Cuando dos artículos sin relación directa contienen afirmaciones genéricas similares, por ejemplo que cierto método mejora el rendimiento, el modelo puede combinarlas para respaldar una afirmación vaga que en realidad debería quedar clasificada como evidencia parcial. Se intentó corregir este problema ajustando las instrucciones dadas al modelo, pero ese ajuste produjo una regresión neta en otros casos y tuvo que revertirse. El problema sigue abierto como una limitación genuina de robustez ante la vaguedad, y no como un error de calibración del banco de pruebas.

El sistema también presenta una limitación en la recuperación de afirmaciones compuestas que requieren evidencia de documentos sin relación entre sí. El orquestador solo vuelve a intentar la búsqueda cuando el resultado inicial es evidencia no localizada, pero no cuando ya existe evidencia parcial para una de las partes de una afirmación compuesta. Esto significa que un documento esperado puede no recuperarse nunca si el otro domina ampliamente los primeros resultados.

Se observó además un grado residual de no determinismo en el motor de inferencia local. Aun con la temperatura del modelo fijada en cero, corridas idénticas del mismo código pueden producir conjuntos de casos fallidos levemente distintos entre sí, aunque el total de casos correctos se mantiene dentro de un rango estable. Este comportamiento está confirmado empíricamente y documentado en `DECISIONS.md`.

El reconocimiento de entidades nombradas mediante spaCy, necesario para completar la sanitización de registros de eventos pedida en la sección de seguridad, sigue bloqueado en el entorno de desarrollo usado para este proyecto, por lo que la sanitización actual se basa únicamente en expresiones regulares.

Por último, la segmentación de documentos en fragmentos se hace contando palabras y no tokens reales del tokenizador del modelo de embeddings, lo cual es una aproximación razonable pero no exacta, y queda documentada como tal en el propio código.

## 8. Conclusiones

El patrón más importante de todo el proyecto puede resumirse en una idea simple. Cuando el modelo de lenguaje falla, la solución real casi nunca consistió en ajustar las instrucciones que se le dan, sino en escribir un chequeo determinístico que no depende de que el modelo se comporte bien. Este patrón se repitió en las citas numéricas inventadas, en las contradicciones no detectadas, en los intentos de inyección de instrucciones y en los archivos maliciosos. El ajuste fino de instrucciones mostró rendimientos claramente decrecientes y, en al menos un caso documentado, produjo una regresión neta que tuvo que revertirse.

El segundo patrón relevante es metodológico. Ninguna corrección se declaró resuelta sin verificarla contra el sistema real, usando el corpus real y el modelo de lenguaje real, y no solamente pruebas con clientes simulados. Varias correcciones que parecían funcionar de forma aislada resultaron insuficientes, o incluso regresivas, y eso solo se descubrió al confirmarlas de esa manera.

## 9. Equipo y plan de trabajo

El equipo quedó conformado por dos integrantes, una decisión documentada en `DECISIONS.md`, a pesar de que el curso exige equipos de tres a cuatro personas, asumiendo el riesgo correspondiente. El reparto real del trabajo, con fechas y tareas completas disponibles en `PLAN_DE_TRABAJO.md` y tomadas directamente del historial de control de versiones, fue el siguiente.

Mónica Salvatierra se encargó del flujo de ingesta y recuperación, del orquestador agéntico, del banco de pruebas y sus métricas de evaluación, de los siete controles de seguridad, y de este documento técnico. Bianca Calderón se encargó de los límites duros de parámetros, de los presupuestos del agente y la validación de identificadores DOI, de corregir un error real en el filtro de permisos, y de la interfaz construida en Streamlit.

## Referencias

El registro completo de decisiones de diseño, incluyendo las iteraciones que no funcionaron y su razonamiento, está disponible en `DECISIONS.md`. El corpus se construyó a partir de la API pública de arXiv mediante `scripts/build_corpus.py`, y los metadatos bibliográficos se contrastaron mediante la API de Crossref.
