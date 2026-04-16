from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from app.schemas import ContextChunk

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "tax_data.json"
CHUNK_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "document_chunks.json"
DEFAULT_TOP_K = 3
MIN_SCORE_THRESHOLD = 1.5

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "both", "can", "do", "for",
    "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or",
    "the", "to", "under", "what", "which", "with", "year",
}


def tokenize(text: str) -> set[str]:
    """Normalize text into searchable tokens."""

    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    return {token for token in normalized.split() if token and token not in STOP_WORDS}


def _collect_search_terms(entry: dict) -> set[str]:
    details = " ".join(entry.get("details", []))
    keywords = " ".join(entry.get("keywords", []))
    searchable_text = " ".join(
        [entry.get("section", ""), entry.get("title", ""), entry.get("description", ""), details, keywords]
    )
    return tokenize(searchable_text)


@lru_cache(maxsize=1)
def load_tax_data() -> list[dict]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_document_chunks() -> list[dict]:
    if not CHUNK_DATA_PATH.exists():
        return []
    with CHUNK_DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def score_entry(question_tokens: set[str], entry: dict) -> float:
    entry_terms = _collect_search_terms(entry)
    overlap = question_tokens & entry_terms
    if not overlap:
        return 0.0

    score = float(len(overlap))
    section_tokens = tokenize(entry.get("section", ""))
    keyword_tokens = tokenize(" ".join(entry.get("keywords", [])))

    if question_tokens & section_tokens:
        score += 2.0
    score += 0.5 * len(question_tokens & keyword_tokens)
    return score


def format_context(chunk: ContextChunk) -> str:
    detail_lines = "\n".join(f"- {detail}" for detail in chunk.details) if chunk.details else "- None"
    keywords = ", ".join(chunk.keywords)
    source_lines = [
        f"Source Name: {chunk.source_name or 'Unknown'}",
        f"Source Type: {chunk.source_type or 'Unknown'}",
    ]
    if chunk.page_number is not None:
        source_lines.append(f"Page Number: {chunk.page_number}")
    if chunk.chunk_id:
        source_lines.append(f"Chunk ID: {chunk.chunk_id}")
    return (
        f"Section: {chunk.section}\n"
        f"Title: {chunk.title}\n"
        f"Tax Year: {chunk.tax_year}\n"
        f"{chr(10).join(source_lines)}\n"
        f"Description: {chunk.description}\n"
        f"Details:\n{detail_lines}\n"
        f"Keywords: {keywords}"
    )


def format_context_blocks(chunks: Iterable[ContextChunk]) -> list[str]:
    return [format_context(chunk) for chunk in chunks]


def get_relevant_context(question: str, top_k: int = DEFAULT_TOP_K) -> list[ContextChunk]:
    """Retrieve the best-matching statutory sections for a question."""

    question_tokens = tokenize(question)
    if not question_tokens:
        return []

    document_chunks = get_relevant_document_context(question_tokens, top_k=top_k)
    if document_chunks:
        return document_chunks

    scored_chunks: list[ContextChunk] = []
    for entry in load_tax_data():
        score = score_entry(question_tokens, entry)
        if score < MIN_SCORE_THRESHOLD:
            continue

        scored_chunks.append(
            ContextChunk(
                section=entry["section"],
                title=entry["title"],
                description=entry["description"],
                details=entry.get("details", []),
                keywords=entry.get("keywords", []),
                tax_year=entry.get("tax_year", "Unknown"),
                score=score,
            )
        )

    scored_chunks.sort(key=lambda chunk: chunk.score, reverse=True)
    return scored_chunks[:top_k]


def _extract_sections(text: str) -> list[str]:
    matches = re.findall(r"\b(?:section|sec\.?)\s+([0-9]{1,3}[A-Z]?(?:\([0-9A-Z]+\))?)", text, flags=re.IGNORECASE)
    compact_matches = re.findall(r"\b([0-9]{1,3}[A-Z]?(?:\([0-9A-Z]+\))?)\b", text)
    normalized = {match.upper() for match in matches + compact_matches if any(char.isdigit() for char in match)}
    return sorted(normalized)


def score_document_chunk(question_tokens: set[str], entry: dict) -> float:
    section_value = entry.get("section") or ", ".join(entry.get("sections", []))
    searchable_text = " ".join(
        [
            section_value,
            entry.get("title", ""),
            entry.get("content", ""),
            " ".join(entry.get("keywords", [])),
            entry.get("source_name", ""),
        ]
    )
    chunk_terms = tokenize(searchable_text)
    overlap = question_tokens & chunk_terms
    if not overlap:
        return 0.0

    score = float(len(overlap))
    section_tokens = tokenize(section_value)
    if question_tokens & section_tokens:
        score += 3.0
    if entry.get("source_type") == "pdf":
        score += 0.25
    return score


def get_relevant_document_context(question_tokens: set[str], top_k: int = DEFAULT_TOP_K) -> list[ContextChunk]:
    scored_chunks: list[ContextChunk] = []
    for entry in load_document_chunks():
        score = score_document_chunk(question_tokens, entry)
        if score < MIN_SCORE_THRESHOLD:
            continue

        content = entry.get("content", "").strip()
        details = [content[i:i + 450] for i in range(0, min(len(content), 900), 450)] or ["No extracted content available."]
        sections = entry.get("sections") or _extract_sections(content)
        scored_chunks.append(
            ContextChunk(
                chunk_id=entry.get("chunk_id"),
                section=", ".join(sections) if sections else "Unknown",
                title=entry.get("title") or entry.get("source_name", "Document chunk"),
                description=content[:500] if content else "No description available.",
                details=details,
                keywords=entry.get("keywords", []),
                tax_year=entry.get("tax_year", "Unknown"),
                source_name=entry.get("source_name"),
                source_type=entry.get("source_type"),
                page_number=entry.get("page_number"),
                score=score,
            )
        )

    scored_chunks.sort(key=lambda chunk: chunk.score, reverse=True)
    return scored_chunks[:top_k]
