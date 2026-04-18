from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaxQuery(BaseModel):
    """Incoming user query for the tax assistant."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="A tax-related natural language question.",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("Question must contain at least 5 non-space characters.")
        return normalized


class ContextChunk(BaseModel):
    """Structured representation of a retrieved tax section or document chunk."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str | None = None
    section: str
    title: str
    description: str
    details: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    tax_year: str
    source_name: str | None = None
    source_type: str | None = None
    page_number: int | None = None
    score: float = Field(default=0.0, ge=0.0)


class TaxResponse(BaseModel):
    """Structured response returned by the LLM and the API."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., min_length=1)
    applicable_sections: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    note: str = Field(..., min_length=1)


class LLMRawResponse(TaxResponse):
    """Alias model for raw LLM payload validation."""


class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
