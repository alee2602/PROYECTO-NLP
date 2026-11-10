import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import requests

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
API_URL = "http://export.arxiv.org/api/query"


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    summary: str
    published: str  # ISO date string, e.g. "2020-05-22T00:00:00Z"
    pdf_url: str
    primary_category: str


def search_arxiv(query: str, max_results: int = 5) -> list[ArxivPaper]:
    """Query the public arXiv API (no key required). Source for Evidentia's
    corpus — open access papers, legal to download and analyze locally
    (anteproyecto sección 7)."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.text)

    papers = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        raw_id = entry.findtext(f"{ATOM_NS}id") or ""
        arxiv_id = raw_id.rsplit("/", 1)[-1]
        title = " ".join((entry.findtext(f"{ATOM_NS}title") or "").split())
        summary = " ".join((entry.findtext(f"{ATOM_NS}summary") or "").split())
        published = entry.findtext(f"{ATOM_NS}published") or ""
        authors = [
            name
            for a in entry.findall(f"{ATOM_NS}author")
            if (name := a.findtext(f"{ATOM_NS}name"))
        ]

        pdf_url = next(
            (
                link.get("href")
                for link in entry.findall(f"{ATOM_NS}link")
                if link.get("title") == "pdf"
            ),
            f"https://arxiv.org/pdf/{arxiv_id}",
        )
        primary_category_el = entry.find(f"{ARXIV_NS}primary_category")
        primary_category = (
            primary_category_el.get("term") if primary_category_el is not None else ""
        )

        papers.append(
            ArxivPaper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                summary=summary,
                published=published,
                pdf_url=pdf_url,
                primary_category=primary_category,
            )
        )
    return papers


def extract_version(arxiv_id: str) -> str:
    """arXiv incluye el número de versión en el propio id (ej. "2309.15217v2"
    -- ver DECISIONS.md: antes se hardcodeaba version="1" al ingerir,
    ignorando este sufijo, lo que dejaba el metadato de versión desalineado
    con la versión real citada en source/texto para 9 de 20 documentos."""
    match = re.search(r"v(\d+)$", arxiv_id)
    return match.group(1) if match else "1"


def download_pdf(url: str, destination: Path) -> None:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination.write_bytes(response.content)
