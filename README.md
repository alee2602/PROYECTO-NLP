# ClaimTrace

Sistema inteligente de análisis y trazabilidad de evidencia en documentos académicos.

Proyecto final del curso CC3103 - Procesamiento de Lenguaje Natural (UVG).

## Qué hace

ClaimTrace analiza afirmaciones presentes en documentos académicos y evalúa si cuentan
con evidencia de respaldo dentro de un corpus de fuentes documentales autorizadas,
usando NLP, RAG y un flujo agéntico. Cada resultado incluye los fragmentos y
referencias documentales usados para facilitar su verificación.

## Estructura del repo

```
data/
  raw/        PDFs originales del corpus (no versionados, ver .gitignore)
  processed/  Chunks + metadatos ya procesados
  eval/       Banco de pruebas de evaluación (casos de prueba)
src/
  ingestion/  Carga, extracción, limpieza, chunking
  retrieval/  Embeddings, índice vectorial, búsqueda híbrida
  agent/      Orquestador y herramientas (extract_claims, search_evidence, etc.)
  schemas/    Modelos Pydantic de validación de entrada/salida
tests/        Pruebas unitarias y de integración
docs/         Anteproyecto y documentación técnica
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Integrantes

- Mónica Salvatierra (22249)
- Bianca Calderón (22272)
