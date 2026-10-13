"""Pydantic schemas for ChronoLex structured output and JSON validation."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.llm import TokenUsage


class StructuredAnswer(BaseModel):
    """Schema model validating the structured LLM answer and source evidence.

    Enforces strict field types (strings only), non-empty values,
    and rejects whitespace-only inputs.
    """

    model_config = ConfigDict(strict=True)

    answer: str = Field(
        ...,
        min_length=1,
        description="The generated answer synthesizing the response.",
    )
    source: str = Field(
        ...,
        min_length=1,
        description=(
            "The source or evidence reference. In demo/educational mode, "
            "represents model-reported attribution, not a verified retrieval citation."
        ),
    )

    @field_validator("answer", "source")
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        """Validates that strings are not empty or solely whitespace."""
        if not isinstance(v, str):
            raise ValueError("Field value must be a string.")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace-only.")
        return stripped


class StructuredRequest(BaseModel):
    """Request payload for the structured output API endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        description="The user question to answer in structured format.",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional custom system prompt. Defaults to strict JSON constraint.",
    )
    temperature: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature. Defaults to 0.0 for deterministic output.",
    )
    use_json_mode: bool = Field(
        default=True,
        description="Whether to request json_object response format if supported by provider.",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Question cannot be empty or whitespace-only.")
        return v.strip()


class StructuredResponse(BaseModel):
    """Validated structured response returned to API clients."""

    answer: str = Field(..., description="The validated answer.")
    source: str = Field(
        ...,
        description=(
            "The source or evidence reference. Note: In demonstration mode without an "
            "active retrieval pipeline, this is model-generated and not authoritative evidence."
        ),
    )
    model: str = Field(..., description="The LLM model name that generated the response.")
    usage: Optional[TokenUsage] = Field(
        default=None,
        description="Token usage and cost estimates if available.",
    )
    retries: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Number of validation retries executed (0 or 1).",
    )
