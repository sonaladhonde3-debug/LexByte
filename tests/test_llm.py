import pytest

from app.llm import build_fallback_response
from app.retriever import get_relevant_context


@pytest.mark.asyncio
async def test_fallback_response_shape() -> None:
    response = build_fallback_response()
    assert response.answer == "insufficient context"
    assert response.applicable_sections == []
    assert response.confidence == 0.0


@pytest.mark.asyncio
async def test_context_shape_for_llm() -> None:
    context = get_relevant_context("How does Section 80D work for health insurance?")
    assert context
    assert "80D" in context[0].section
