from __future__ import annotations

import json
import logging
import os
from typing import Iterable

from google import genai
from google.genai import types, errors
from pydantic import ValidationError
from dotenv import load_dotenv

load_dotenv()

from app.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retriever import format_context_blocks
from app.schemas import ContextChunk, TaxResponse

logger = logging.getLogger(__name__)

DEFAULT_NOTE = (
    "This response is based only on the retrieved statutory context and is not legal or financial advice. "
    "Please consult a chartered accountant or tax professional."
)

RETRYABLE_ERRORS = (errors.APIError,)


def get_gemini_client() -> genai.client.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=api_key)


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def build_response_schema() -> types.Schema:
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "answer": types.Schema(type=types.Type.STRING),
            "applicable_sections": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
            ),
            "sources": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
            ),
            "confidence": types.Schema(type=types.Type.NUMBER),
            "note": types.Schema(type=types.Type.STRING),
        },
        required=["answer", "applicable_sections", "confidence", "note"],
    )


def build_fallback_response(
    *,
    answer: str = "insufficient context",
    applicable_sections: list[str] | None = None,
    sources: list[str] | None = None,
    confidence: float = 0.0,
    note: str = DEFAULT_NOTE,
) -> TaxResponse:
    return TaxResponse(
        answer=answer,
        applicable_sections=applicable_sections or [],
        sources=sources or [],
        confidence=confidence,
        note=note,
    )


async def _raw_search_pass(question: str) -> str:
    """Execute a raw Google Search pass to feed back into the JSON engine."""
    client = get_gemini_client()
    try:
        response = await client.aio.models.generate_content(
            model=get_model_name(),
            contents=f"Conduct a web search regarding Indian Income Tax for the following query, and summarize the current facts, dates, and sections. INCLUDE THE URLs OF THE WEBSITES YOU REFERENCED: {question}",
            config=types.GenerateContentConfig(
                response_mime_type="text/plain",
                tools=[{'google_search': {}}]
            )
        )
        return (response.text or "").strip()
    except Exception as exc:
        logger.warning("Live web search failed: %s", exc)
        return ""


async def _invoke_llm(question: str, context_blocks: Iterable[str]) -> str:
    client = get_gemini_client()
    prompt = f"{SYSTEM_PROMPT}\n\n{build_user_prompt(question, context_blocks)}"
    
    response = await client.aio.models.generate_content(
        model=get_model_name(),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=build_response_schema()
        )
    )
    return (response.text or "").strip()


async def generate_tax_answer(question: str, context: list[ContextChunk]) -> TaxResponse:
    """Generate a grounded JSON answer using retrieved context and live web data."""

    web_knowledge = await _raw_search_pass(question)

    if not context and not web_knowledge:
        return build_fallback_response()

    context_blocks = list(format_context_blocks(context))
    if web_knowledge:
        context_blocks = [f"--- LIVE WEB SEARCH DATA ---\n{web_knowledge}\n---------------------"] + context_blocks

    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            raw_output = await _invoke_llm(question, context_blocks)
            payload = json.loads(raw_output)
            validated = TaxResponse.model_validate(payload)
            if not validated.note.strip():
                validated.note = DEFAULT_NOTE
            return validated
        except ValidationError as exc:
            logger.warning("LLM response validation failed on attempt %s: %s", attempt, exc)
            last_error = exc
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON on attempt %s: %s", attempt, exc)
            last_error = exc
        except RETRYABLE_ERRORS as exc:
            logger.warning("Transient LLM error on attempt %s: %s", attempt, exc)
            last_error = exc
        except Exception as exc:
            logger.warning("Unexpected error on attempt %s: %s", attempt, exc)
            last_error = exc

    logger.error("Falling back after LLM failure: %s", last_error)
    return build_fallback_response(
        answer="Unable to generate a reliable answer from the available context at this time.",
        applicable_sections=[chunk.section for chunk in context],
        confidence=0.0,
    )
