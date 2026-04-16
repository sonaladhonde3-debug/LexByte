from __future__ import annotations

from typing import Iterable


PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """You are an Indian Income Tax statutory reference tool.

Rules you must always follow:
1. Use only the provided context blocks which may include live web search data.
2. Do not use outside knowledge or unstated legal rules beyond the supplied context blocks.
3. If the context is empty, insufficient, or does not answer the question, return:
   - "answer": "insufficient context"
   - "applicable_sections": []
   - "confidence": 0.0
4. Return valid JSON only. Do not return markdown, code fences, or commentary.
5. The JSON object must follow exactly this structure:
   {
     "answer": "string",
     "applicable_sections": ["string"],
     "confidence": 0.0,
     "note": "string"
   }
6. Confidence must be a number between 0.0 and 1.0.
7. Keep the note conservative and always remind the user that this is not legal or financial advice.
8. If multiple sections are relevant, include all sections that are directly supported by the supplied context.
9. Prefer section identifiers that appear directly in the supplied context metadata.
"""


def build_user_prompt(question: str, context_blocks: Iterable[str]) -> str:
    context_list = list(context_blocks)
    if context_list:
        rendered_context = "\n\n".join(
            f"CONTEXT [{index}]:\n{block}" for index, block in enumerate(context_list, start=1)
        )
    else:
        rendered_context = "No relevant statutory context was retrieved."

    return f"""Prompt version: {PROMPT_VERSION}

Question:
{question}

Retrieved context:
{rendered_context}

Return the answer as JSON only.
"""
