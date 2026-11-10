# Evidentia

Sistema inteligente de análisis y trazabilidad de evidencia en documentos académicos.

Proyecto final del curso CC3103 - Procesamiento de Lenguaje Natural (UVG).

## Qué hace

Evidentia analiza afirmaciones presentes en documentos académicos y evalúa si cuentan
con evidencia de respaldo dentro de un corpus de fuentes documentales autorizadas,
usando NLP, RAG y un flujo agéntico. Cada resultado incluye los fragmentos y
referencias documentales usados para facilitar su verificación.

## Estructura del repo

```
data/
  raw/        PDFs originales del corpus (no versionados, ver .gitignore)
  processed/  documents.json (metadata, versionado) y chunks.jsonl (texto, no versionado)
  eval/       Banco de pruebas de evaluación (casos de prueba)
src/
  ingestion/  Carga, extracción, limpieza, chunking, fuente de arXiv
  retrieval/  Embeddings, índice vectorial, búsqueda híbrida
  agent/      Orquestador, herramientas (extract_claims, search_evidence, etc.) y cliente LLM
  schemas/    Modelos Pydantic de metadatos y del esquema de salida obligatorio
scripts/      Scripts de uso manual (armar corpus, probar el LLM)
tests/        Pruebas unitarias y de integración
docs/         Anteproyecto y documentación técnica
```

## Documentos del repo

| Archivo | Para qué sirve |
|---|---|
| `TODO.md` | Lista de tareas pendientes, organizada por las 6 fases/ciclos del curso (Anteproyecto, Línea Base, Mejora Técnica, Evaluación, Seguridad, Demostración y Defensa). |
| `DECISIONS.md` | Log de decisiones de diseño e iteraciones: contexto, qué se decidió, alternativas consideradas, estado y gaps abiertos. Base para las secciones de "limitaciones" y "trabajo futuro" del documento técnico final. |
| `CLAUDE.md` | Reglas de trabajo para Claude Code en este repo (estilo de commits, qué no se sube a git, contexto del proyecto). |
| `requirements.txt` | Dependencias de Python del proyecto. |

## Setup

**Usamos un entorno conda, no `venv`** (ver `DECISIONS.md`: `torch` instalado vía
`pip` en un `venv` quedó bloqueado por Smart App Control de Windows; la copia
de `torch` instalada vía `conda` no tiene ese problema).

```powershell
conda create -n evidentia python=3.12 -y
conda install -n evidentia pytorch cpuonly -c pytorch -y
conda activate evidentia
pip install -r requirements.txt
```

Si en tu máquina `pytorch` desde el canal `pytorch` da un error de versión con
`transformers` (pide `torch >= 2.6`), instala una build más nueva, por ejemplo:

```powershell
conda search "pytorch[version='>=2.6']" -c pytorch   # ver qué builds hay para tu Python
conda install -n evidentia pytorch=2.15.0 -c pytorch -y   # ajustar versión/build según lo que encuentres
```

Para correr cualquier script del proyecto, usar el Python de este entorno:

```powershell
C:\Users\<tu-usuario>\anaconda3\envs\evidentia\python.exe scripts\build_corpus.py
C:\Users\<tu-usuario>\anaconda3\envs\evidentia\python.exe -m pytest tests/
```

(o `conda activate evidentia` primero y usar `python`/`pytest` directo).

## Datos: cómo regenerarlos en tu máquina

`data/raw/` (PDFs) y `data/processed/chunks.jsonl` (texto completo de los chunks)
**no se suben a git** — ni los PDFs originales ni el texto extraído de papers de
terceros se redistribuyen por este medio (ver `DECISIONS.md`). Lo único versionado
es `data/processed/documents.json`, que solo tiene metadata bibliográfica.

Si clonas el repo de cero, para tener los datos localmente corre:

```powershell
conda activate evidentia
python scripts\build_corpus.py
```

Esto descarga los 10 papers de arXiv (D01-D10) a `data/raw/`, los procesa con el
pipeline de ingesta, y regenera `data/processed/documents.json` y `chunks.jsonl`.
Es reproducible: siempre arma el mismo corpus (mismas queries, mismo filtro de
duplicados/tamaño) salvo que arXiv cambie qué devuelve como más relevante para esas
búsquedas.

## Usar el modelo generativo con LM Studio

El sistema necesita un LLM para `evaluate_evidence` (clasificar afirmaciones contra
evidencia). Por defecto el proyecto apunta a **LM Studio corriendo en tu propia
máquina** (gratis, privado, sin API key) — ver `src/agent/llm_client.py` y
`DECISIONS.md` para el porqué.

### 1. Instalar LM Studio

Descargar de [lmstudio.ai](https://lmstudio.ai) e instalar normalmente.

### 2. Descargar un modelo

Abrir LM Studio → pestaña de búsqueda/Discover → buscar un modelo instruct de
**solo texto** (NO uno "VL"/vision-language — esos reservan capacidad para
imágenes y razonan peor en texto puro). Recomendado: `qwen/qwen3.5-9b`
(el que usa este repo en las pruebas manuales — ver `DECISIONS.md`: con la
variante VL de 7B el sistema fallaba en casos de contradicción de forma
irresoluble por prompt; con este modelo de texto de 9B se resolvió solo
cambiando el modelo). Tiene que soportar **salida estructurada (JSON
Schema)**; la mayoría de modelos "instruct" recientes de Qwen, Llama o
Mistral lo soportan.

### 3. Levantar el servidor local

Dos formas, cualquiera funciona:

**Desde la app**: pestaña del servidor local (ícono `<->`) → seleccionar el modelo
descargado → "Start Server". Queda escuchando en `http://localhost:1234`.

**Desde la terminal** (más rápido, no hay que abrir la ventana de LM Studio):

```powershell
lms server start
lms load qwen/qwen3.5-9b --context-length 16384
lms status   # confirma que el server está ON y el modelo cargado
```

**Importante**: usar `--context-length 16384` (o más). Con el contexto por
defecto (4096 tokens) el sistema falla con `top_k=5` evidencias — 5 chunks de
~450 palabras más el prompt superan ese límite (ver `DECISIONS.md`).

(`lms` se instala junto con LM Studio, normalmente en
`%USERPROFILE%\.lmstudio\bin\lms.exe`.)

### 4. Configurar las variables de entorno

Copiar `.env.example` a `.env` y ajustar `LLM_MODEL` al identificador exacto del
modelo que cargaste (el mismo nombre que usas en `lms load`):

```bash
copy .env.example .env
```

```
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=qwen/qwen3.5-9b
```

### 5. Probar que funciona

```powershell
conda activate evidentia
python scripts\check_llm.py
```

Si todo está bien, imprime un `EvidentiaOutput` válido (clasificación, fuentes, etc.)
en vez de la respuesta de abstención por fallo. Si falla, revisar que el servidor
esté `ON` (`lms status`) y que `LLM_MODEL` coincida exactamente con el modelo cargado.

### Nota sobre el SDK de OpenAI

El proyecto **no usa el SDK `openai`**, habla directo por REST con `requests` —
en Windows, el SDK falló por un binario nativo (`jiter`) bloqueado por Smart App
Control. Si cambian de proveedor (a una API en la nube en vez de LM Studio), solo
hay que cambiar las variables de entorno, no el código — pero confirmar que ese
proveedor también soporte `response_format: json_schema` (ver `DECISIONS.md`).

## Integrantes

- Mónica Salvatierra (22249)
- Bianca Calderón (22272)
