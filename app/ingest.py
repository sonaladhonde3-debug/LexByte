from __future__ import annotations

import json
import re
from pathlib import Path
from time import perf_counter

from docx import Document
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
OUTPUT_PATH = PROJECT_ROOT / "data" / "document_chunks.json"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
CHUNK_SIZE = 1400
CHUNK_OVERLAP = 200


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_sections(text: str) -> list[str]:
    pattern = r"\b(?:section|sec\.?)\s+([0-9]{1,3}[A-Z]?(?:\([0-9A-Z]+\))?)"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    return sorted({match.upper() for match in matches})


def derive_keywords(text: str, limit: int = 12) -> list[str]:
    stop_words = {
        "the", "and", "for", "that", "with", "from", "this", "have", "under",
        "shall", "where", "which", "there", "such", "into", "their", "being",
        "will", "would", "could", "should", "about", "your", "tax", "income",
    }
    tokens = re.findall(r"[A-Za-z0-9()/-]+", text.lower())
    frequencies: dict[str, int] = {}
    for token in tokens:
        if len(token) < 3 or token in stop_words:
            continue
        frequencies[token] = frequencies.get(token, 0) + 1
    return [token for token, _ in sorted(frequencies.items(), key=lambda item: item[1], reverse=True)[:limit]]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def read_pdf(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append((index, text))
    return pages


def read_docx(path: Path) -> list[tuple[int, str]]:
    document = Document(str(path))
    text = clean_text(" ".join(paragraph.text for paragraph in document.paragraphs))
    return [(1, text)] if text else []


def read_txt(path: Path) -> list[tuple[int, str]]:
    text = clean_text(path.read_text(encoding="utf-8"))
    return [(1, text)] if text else []


def extract_pages(path: Path) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix == ".docx":
        return read_docx(path)
    if suffix == ".txt":
        return read_txt(path)
    return []


def ingest_documents() -> list[dict]:
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    chunks: list[dict] = []
    for path in sorted(DOCUMENTS_DIR.iterdir()):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS or not path.is_file():
            continue

        source_type = path.suffix.lower().lstrip(".")
        started_at = perf_counter()
        print(f"Processing {path.name} ...")
        try:
            file_chunk_count = 0
            for page_number, page_text in extract_pages(path):
                for chunk_index, chunk in enumerate(chunk_text(page_text), start=1):
                    sections = extract_sections(chunk)
                    chunks.append(
                        {
                            "chunk_id": f"{path.stem}-p{page_number}-c{chunk_index}",
                            "source_name": path.name,
                            "source_type": source_type,
                            "page_number": page_number,
                            "title": path.stem.replace("_", " ").title(),
                            "content": chunk,
                            "sections": sections,
                            "section": ", ".join(sections),
                            "keywords": derive_keywords(chunk),
                            "tax_year": "Source document",
                        }
                    )
                    file_chunk_count += 1
            elapsed = perf_counter() - started_at
            print(f"Completed {path.name}: {file_chunk_count} chunks in {elapsed:.1f}s")
        except Exception as exc:
            elapsed = perf_counter() - started_at
            print(f"Skipped {path.name} after {elapsed:.1f}s due to error: {exc}")

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(chunks, file, indent=2, ensure_ascii=False)
    return chunks


if __name__ == "__main__":
    result = ingest_documents()
    print(f"Ingested {len(result)} chunks into {OUTPUT_PATH}")
