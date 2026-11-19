# Guion de demostración

## Evidentia, quince minutos

La estructura pedida por el curso distribuye el tiempo en dos minutos para el problema y el usuario, tres minutos para la arquitectura, cuatro minutos para la demostración en vivo, tres minutos para las métricas, dos minutos para la seguridad y un minuto para las conclusiones.

## Antes de empezar

Esta lista debe revisarse antes de la presentación, no durante ella.

El servidor de LM Studio debe estar corriendo con el modelo `qwen/qwen3.5-9b` cargado con un contexto de dieciséis mil trescientos ochenta y cuatro tokens. El contexto por defecto, de cuatro mil noventa y seis tokens, hace fallar casi todas las evaluaciones de forma silenciosa, así que conviene verificar con `lms ps` antes de empezar en lugar de asumir que quedó bien configurado.

El corpus debe estar construido, de modo que `data/processed/chunks.jsonl` exista.

La interfaz debe haberse abierto y probado al menos una vez antes de la presentación, corriendo `streamlit run app/streamlit_app.py`, porque la primera indexación tarda unos segundos.

Conviene tener a mano un PDF corto de prueba para la subida en vivo, que no esté ya incluido en el corpus, de modo que se note la diferencia entre un documento conocido y uno nuevo.

Conviene también tener un plan de respaldo si algo falla durante la demostración en vivo, porque LM Studio tiene un error conocido que ocasionalmente hace fallar la generación con un mensaje sobre una pila de gramática vacía, según se documenta en `DECISIONS.md`. Tener a mano una captura de pantalla o el contenido de `logs/eval_results.json` permite seguir adelante sin depender por completo de que la demostración en vivo funcione a la primera.

Como reparto sugerido para un equipo de dos personas, que puede ajustarse según lo que pida el curso, Mónica puede encargarse de las secciones de arquitectura, métricas y seguridad, por haber implementado esas partes directamente, mientras que Bianca puede encargarse de las secciones de problema y usuario, y de la demostración en vivo con la interfaz que ella construyó. Las conclusiones pueden presentarse entre ambas.

## Primera sección, problema y usuario, dos minutos

Verificar a mano si una afirmación de un documento académico está realmente respaldada por su fuente es lento y propenso al error, sobre todo cuando hay decenas de referencias y no hay tiempo de releer cada una.

El usuario objetivo es alguien que revisa un documento académico, ya sea estudiante, investigador o revisor, y quiere saber, afirmación por afirmación, si el corpus disponible la respalda, la contradice o no dice nada al respecto.

La promesa del sistema no es que haya que confiar ciegamente en el modelo de lenguaje, sino que cada respuesta venga acompañada de la cita exacta, con documento, página y fragmento, de modo que la persona pueda verificarla ella misma en pocos segundos, y que el sistema se abstenga en lugar de inventar cuando no existe evidencia real.

## Segunda sección, arquitectura, tres minutos

Conviene mostrar el diagrama descrito en la sección tres de `DOCUMENTO_TECNICO.md`, o dibujarlo en vivo, siguiendo el flujo desde la extracción de afirmaciones hasta el recuperador híbrido y la evaluación de evidencia con sus tres verificaciones determinísticas, para terminar en la salida estructurada del sistema.

El punto central que conviene explicar, no solo mostrar, es que el modelo de lenguaje no tiene la última palabra. Después de que el modelo clasifica una afirmación, un conjunto de verificaciones de código comprueba si la cita existe de verdad entre lo recuperado, si las cifras que menciona la afirmación aparecen literalmente en el texto citado, y si hay algún patrón de manipulación en la afirmación o en el documento. Si alguna de estas verificaciones falla, el sistema degrada la clasificación o se abstiene, sin importar qué tan convencido suene el modelo.

Conviene mencionar brevemente que la recuperación es híbrida, combinando búsqueda semántica y léxica, porque las consultas están en español y el corpus en inglés, y la búsqueda puramente semántica tiende a perder términos técnicos exactos como BM25 o RAGAS.

## Tercera sección, demostración en vivo, cuatro minutos

Se sugieren dos flujos cortos dentro de la interfaz construida con Streamlit.

El primero consiste en verificar una afirmación suelta, usando la pestaña correspondiente, escribiendo una afirmación conocida del corpus, por ejemplo sobre FAISS o sobre BM25, y mostrando después la clasificación obtenida, la cita exacta con su fragmento y el JSON de salida completo.

El segundo consiste en subir un PDF nuevo, usando la pestaña de análisis de documentos, dejando que el sistema extraiga sus afirmaciones, y mostrando el resumen por nivel de evidencia, incluyendo al menos un caso de evidencia parcial o de evidencia no localizada, para demostrar que el sistema no fuerza todo hacia una clasificación de evidencia suficiente.

Si el tiempo apremia, conviene priorizar el primer flujo, que es más rápido y da más control sobre el resultado, y mencionar el segundo solamente de palabra.

Conviene recordar, para no quedarse en silencio esperando, que con el modelo `qwen/qwen3.5-9b` cada afirmación tarda entre diez y veinticinco segundos en promedio, con un percentil noventa y cinco de alrededor de cuarenta a cincuenta segundos, así que conviene tener la consulta lista de antemano y lanzarla justo al empezar a hablar de esta sección.

## Cuarta sección, métricas, tres minutos

Conviene mostrar la tabla de resultados de la sección seis de `DOCUMENTO_TECNICO.md`, con el Recall, el MRR y la exactitud de clasificación, junto con la comparación entre la línea base de la fase dos, puramente semántica, y la versión mejorada de la fase tres, híbrida. Este es el dato más convincente, porque muestra que la mejora en la recuperación se traduce directamente en una mejora grande de la clasificación final, y no es una mejora aislada sin impacto real.

Conviene mencionar explícitamente que el Recall se verificó mediante un estudio de ablación y mediante un corpus duplicado con distractores reales, para que el número no suene inflado.

## Quinta sección, seguridad, dos minutos

Conviene mostrar la tabla de los siete controles de seguridad de la sección cinco de `DOCUMENTO_TECNICO.md`, y elegir uno o dos casos para explicar con algo más de detalle. Se recomienda el primero, porque es fácil de entender en treinta segundos, ya que si alguien le dice al sistema que ignore sus instrucciones, el sistema ignora a quien lo dice y no al revés, y también el quinto, porque conecta directamente con el problema planteado en la primera sección, ya que el sistema no inventa citas.

Conviene mencionar de paso que durante este trabajo se encontraron y corrigieron dos errores reales, en lugar de dar la impresión de que todo funcionó a la primera, porque eso le da credibilidad a la presentación.

## Sexta sección, conclusiones, un minuto

Conviene cerrar con el patrón central del proyecto, resumido en una idea simple. Cuando el modelo de lenguaje falla, la solución casi nunca consistió en ajustar las instrucciones que se le dan, sino en escribir un chequeo de código que no depende de que el modelo se comporte bien, y cada corrección se verificó contra el sistema real, no solamente de forma aislada.

## Preguntas esperables

Conviene preparar una respuesta corta para cada una de las siguientes preguntas.

Si preguntan por qué no se usó GPT-4 o Claude en lugar de un modelo local, la respuesta es que durante el desarrollo se priorizó el costo y la privacidad, y que el cliente habla directamente por REST, de modo que cambiar de proveedor es solamente cuestión de variables de entorno y no de código, siempre que ese proveedor soporte el formato de respuesta estructurada JSON Schema.

Si preguntan qué tan confiable es el Recall cercano al noventa y cinco por ciento, la respuesta es que se verificó con un estudio de ablación comparando la recuperación puramente semántica, la puramente léxica y la híbrida, y con el corpus duplicado a veinte documentos con distractores reales, de modo que no se sostiene por un solo truco.

Si preguntan qué pasa si alguien sube un PDF malicioso, la respuesta es que el sexto control de seguridad valida el tipo de archivo, su tamaño, su número de páginas, si está cifrado y si contiene JavaScript embebido antes de procesar nada, y que además el texto invisible se filtra durante la extracción, como parte del segundo control.

Si preguntan qué falta, la respuesta puede apoyarse en `TODO.md` y en `STATUS.md`, mencionando la detección de nombres propios en los registros de eventos, bloqueada por spaCy en este entorno, y la limitación de recuperación en afirmaciones compuestas entre documentos sin relación entre sí, descrita en la sección siete de `DOCUMENTO_TECNICO.md`.
