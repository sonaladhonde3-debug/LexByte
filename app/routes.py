from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.llm import generate_tax_answer
from app.retriever import get_relevant_context
from app.schemas import HealthResponse, TaxQuery, TaxResponse

logger = logging.getLogger(__name__)

router = APIRouter()
UI_INDEX = Path(__file__).resolve().parent / "ui" / "index.html"

RetrieverDependency = Callable[[str], list]
LLMDependency = Callable[[str, list], Awaitable[TaxResponse]]


def get_retriever() -> RetrieverDependency:
    return get_relevant_context


def get_llm_service() -> LLMDependency:
    return generate_tax_answer


def enforce_rate_limit() -> None:
    """Production hook for future rate limiting or auth logic."""


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Simple health-check endpoint for uptime probes."""

    return HealthResponse(
        status="ok",
        version=os.getenv("APP_VERSION", "0.1.0"),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/", include_in_schema=False)
async def serve_ui() -> FileResponse:
    """Serve the lightweight frontend UI."""

    return FileResponse(UI_INDEX)


@router.post("/ask", response_model=TaxResponse, tags=["tax"])
async def ask_tax_question(
    payload: TaxQuery,
    _: None = Depends(enforce_rate_limit),
    retriever: RetrieverDependency = Depends(get_retriever),
    llm_service: LLMDependency = Depends(get_llm_service),
) -> TaxResponse:
    """
    Retrieve relevant statutory context and answer a tax question.

    The response is always grounded in the retrieved dataset and returned as structured JSON.
    """

    context = retriever(payload.question)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant statutory context found for the supplied question.",
        )

    try:
        return await llm_service(payload.question, context)
    except RuntimeError as exc:
        logger.exception("LLM service is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is not configured.",
        ) from exc
    except ValueError as exc:
        logger.exception("Invalid JSON received from LLM")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="LLM returned an invalid structured response.",
        ) from exc
    except TimeoutError as exc:
        logger.exception("LLM call timed out")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM request timed out.",
        ) from exc
