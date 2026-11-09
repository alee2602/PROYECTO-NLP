# CLAUDE.md

Reglas para trabajar en este repositorio (Evidentia — Proyecto Final CC3103).

## Commits

- **Claude nunca ejecuta `git commit` en este repo.** Solo la usuaria hace los commits. Claude puede sugerir el mensaje (en inglés, ver abajo) pero no debe correr el comando, ni siquiera si parece que se está pidiendo.
- **No agregar línea de coautoría de Claude** (`Co-Authored-By: Claude...`) en los mensajes de commit de este repo. Los commits deben quedar atribuidos únicamente a la persona que los hizo.
- **Los mensajes de commit deben sugerirse en inglés.**

## Material del curso

- Los archivos descargados del curso (`.pptx`, `.docx`, `.pdf` — enunciado del proyecto, plantilla de anteproyecto, slides) **no se suben a git**. Ya están excluidos vía `.gitignore` (`*.pptx`, `*.docx`, `*.pdf`).
- Esto también cubre cualquier PDF del corpus académico que se vaya armando en `data/raw/` — tampoco se sube a git.

## Contexto del proyecto

- **Proyecto**: Evidentia (antes "ClaimTrace") — sistema de análisis y trazabilidad de evidencia en documentos académicos (NLP + RAG + agéntico).
- **Curso**: CC3103 Procesamiento de Lenguaje Natural, UVG. Vale 30% de la nota final.
- **Integrantes actuales**: Mónica Salvatierra (22249), Bianca Calderón (22272). El curso exige equipos de 3-4, falta completar el equipo.
- **Stack**: Python, Streamlit, PyMuPDF, spaCy, Sentence Transformers, FAISS, BM25, LangGraph, Pydantic.
