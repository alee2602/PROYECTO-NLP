# CLAUDE.md

Reglas para trabajar en este repositorio (ClaimTrace — Proyecto Final CC3103).

## Commits

- **No agregar línea de coautoría de Claude** (`Co-Authored-By: Claude...`) en los mensajes de commit de este repo. Los commits deben quedar atribuidos únicamente a la persona que los hizo.
- No comitear sin que el usuario lo pida explícitamente.
- **Los mensajes de commit deben sugerirse en inglés.**

## Material del curso

- Los archivos descargados del curso (`.pptx`, `.docx`, `.pdf` — enunciado del proyecto, plantilla de anteproyecto, slides) **no se suben a git**. Ya están excluidos vía `.gitignore` (`*.pptx`, `*.docx`, `*.pdf`).
- Esto también cubre cualquier PDF del corpus académico que se vaya armando en `data/raw/` — tampoco se sube a git.

## Contexto del proyecto

- **Proyecto**: ClaimTrace — sistema de análisis y trazabilidad de evidencia en documentos académicos (NLP + RAG + agéntico).
- **Curso**: CC3103 Procesamiento de Lenguaje Natural, UVG. Vale 30% de la nota final.
- **Integrantes actuales**: Mónica Salvatierra (22249), Bianca Calderón (22272). El curso exige equipos de 3-4, falta completar el equipo.
- **Stack**: Python, Streamlit, PyMuPDF, spaCy, Sentence Transformers, FAISS, BM25, LangGraph, Pydantic.
