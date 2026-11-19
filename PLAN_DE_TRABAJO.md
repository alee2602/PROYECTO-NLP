# Plan de trabajo real

## Para la sección de plan de trabajo del anteproyecto

El anteproyecto original dejó esa sección con fechas marcadas como pendientes y con tareas asignadas a un tercer integrante hipotético que nunca llegó a unirse al equipo, según la decisión de equipo documentada en `DECISIONS.md` de quedarse en dos integrantes. Esta tabla reemplaza esos espacios pendientes con lo que realmente ocurrió, con el responsable y la fecha real de cada tarea tomados directamente del historial de control de versiones y no estimados de memoria, de modo que pueda copiarse tal cual a esa sección.

| Fase | Tarea | Responsable | Fecha |
|---|---|---|---|
| Anteproyecto | Estructura del repositorio, cambio de nombre del proyecto a Evidentia, cierre de la fase | Mónica | 4 al 9 de noviembre de 2026 |
| Línea base | Flujo de ingesta de documentos, con la extracción, la limpieza y la segmentación, más los esquemas de Pydantic | Mónica | 9 de noviembre de 2026 |
| Línea base | Recuperación semántica con FAISS y cliente del modelo de lenguaje por REST directo, sin el SDK de OpenAI | Mónica | 9 de noviembre de 2026 |
| Línea base | Corpus inicial de diez artículos de arXiv y validación de la recuperación | Mónica | 9 de noviembre de 2026 |
| Mejora técnica | Recuperación híbrida con BM25 propio y refuerzo de identificadores, limpieza de texto entre idiomas | Mónica | 10 de noviembre de 2026 |
| Mejora técnica | Validación determinística de citas y migración del entorno de desarrollo a conda | Mónica | 10 de noviembre de 2026 |
| Mejora técnica | Extracción de afirmaciones y orquestador agéntico con LangGraph, con su filtro de vaguedad | Mónica | 10 de noviembre de 2026 |
| Evaluación | Banco de veinticinco casos de prueba y su primer corrida real contra el sistema | Mónica | 10 de noviembre de 2026 |
| Evaluación | Estudio de ablación de recuperación y verificación del Recall sobre el corpus duplicado | Mónica | 10 de noviembre de 2026 |
| Evaluación | Cambio de modelo de lenguaje y corrección de los errores de clasificación relacionados con identificadores de arXiv y con la metadata de versión | Mónica | 10 de noviembre de 2026 |
| Evaluación | Límites duros de parámetros para el número de resultados y de afirmaciones | Bianca | 10 de noviembre de 2026 |
| Evaluación | Confirmación del caso de prueba sobre parámetros fuera de rango contra el sistema real | Mónica | 11 de noviembre de 2026 |
| Evaluación | Corrección de la métrica de Recall para afirmaciones compuestas, incorporación del MRR, de la latencia y del consumo de tokens, y comparación entre la línea base y la versión mejorada | Mónica | 19 de noviembre de 2026 |
| Seguridad | Implementación y verificación de los siete controles de seguridad adversarios | Mónica | 11 de noviembre de 2026 |
| Seguridad | Presupuestos del agente para iteraciones, llamadas al modelo y llamadas externas, y validación de identificadores DOI | Bianca | 14 de noviembre de 2026 |
| Seguridad | Corrección del filtro de permisos, que se aplicaba después de recortar el conjunto de candidatos | Bianca | 14 de noviembre de 2026 |
| Seguridad | Decisión de equipo de que la ausencia de identidad debe ocultar los fragmentos privados por defecto | Mónica | 19 de noviembre de 2026 |
| Evaluación | Incorporación al flujo de evaluación del caso de prueba sobre confirmación humana ante la ampliación de búsqueda, que estaba definido en el banco de pruebas pero nunca se ejecutaba de verdad | Mónica | 19 de noviembre de 2026 |
| Demostración y defensa | Documento técnico, guion de demostración y actualización de este plan de trabajo | Mónica | 19 de noviembre de 2026 |

## Tareas que no estaban contempladas en el plan original

Algunas tareas no fueron anticipadas explícitamente en el anteproyecto, pero resultaron necesarias y se llevaron a cabo de todas formas.

La interfaz construida con Streamlit no estaba asignada a nadie en particular, ya que el anteproyecto la ubicaba de forma genérica en la fase de mejora técnica, a cargo del integrante que nunca se unió al equipo. En la práctica, Bianca la construyó más adelante, en paralelo a la fase de seguridad, el 16 de noviembre de 2026. Esa interfaz permite subir un PDF, analizar sus afirmaciones o verificar una afirmación suelta, y usa de verdad los controles de seguridad ya implementados, como la identidad de sesión del control de permisos y la validación de archivos.

La migración del entorno de desarrollo de un `venv` convencional a un entorno de conda tampoco estaba en el plan. Resultó necesaria porque el Control de aplicaciones de Windows bloqueaba binarios nativos instalados mediante `pip`, como `torch` y el SDK de `openai`, según se explica en `DECISIONS.md`.

También fue necesario reconciliar dos implementaciones paralelas de la fase de seguridad, porque Mónica y Bianca la trabajaron por separado sin coordinarse primero. El problema se resolvió conservando la implementación de Mónica, que ya estaba verificada, y añadiéndole las piezas adicionales que Bianca había construido por su lado, como los presupuestos del agente, la validación de DOI y la corrección del filtro de permisos. La lección que queda para las fases restantes es coordinar de antemano quién trabaja en qué módulo, en lugar de reconciliar después.

Por último, en el camino se encontraron y corrigieron dos errores reales que no estaban relacionados con la tarea que se estaba realizando en ese momento. Uno estaba en `pdf_loader.py`, que cerraba el documento antes de volver a leer el número de páginas dentro del mensaje de error, y apareció al escribir pruebas reales para el control de archivos maliciosos. El otro era un error de permisos de Windows al limpiar un directorio temporal después de que la biblioteca de manejo de PDF fallara al abrir un archivo inválido, y apareció al correr las pruebas después de incorporar los cambios de Bianca al repositorio local.

## Reasignación de las tareas del tercer integrante

El anteproyecto original asignaba al tercer integrante hipotético la interfaz, en la fase de mejora técnica, y la evaluación, en la fase de evaluación. Con el equipo confirmado en dos personas, el reparto real quedó de la siguiente manera, no por una asignación decidida de antemano sino por cómo se distribuyó el trabajo en la práctica.

La evaluación quedó a cargo de Mónica, incluyendo el banco de pruebas, el programa que lo ejecuta, las métricas, el estudio de ablación y la comparación entre la línea base y la versión mejorada. La interfaz quedó a cargo de Bianca, construida durante la fase de seguridad en lugar de la fase de mejora técnica, porque el equipo priorizó tener primero un flujo agéntico y una seguridad sólidos antes de exponerlos mediante una interfaz.
