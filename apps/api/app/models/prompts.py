"""Pydantic models for prompt engineering experiments."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.llm import TokenUsage


class PromptExperimentMode(str, Enum):
    SYSTEM_USER = "system_user"
    COMPARE = "compare"
    JSON = "json"
    GROUNDING = "grounding"


class PromptExperimentRequest(BaseModel):
    mode: PromptExperimentMode = Field(
        ...,
        description="Experiment mode: 'system_user', 'compare', 'json', or 'grounding'.",
    )
    question: Optional[str] = Field(
        default=None,
        description="Question to ask (required for 'grounding' mode).",
    )
    context: Optional[str] = Field(
        default=None,
        description="Regulatory context text (used for 'grounding' mode).",
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="Optional custom user prompt for 'json' or 'system_user' modes.",
    )


class PromptComparisonItem(BaseModel):
    prompt_type: str
    prompt: str
    answer: str
    usage: Optional[TokenUsage] = None


class JSONConstraintResult(BaseModel):
    raw_answer: str
    is_valid_json: bool
    parsed_json: Optional[Dict[str, Any]] = None
    parsing_error: Optional[str] = None
    usage: Optional[TokenUsage] = None


class GroundingResult(BaseModel):
    question: str
    context: str
    answer: str
    evidence_sufficient: bool
    usage: Optional[TokenUsage] = None


class PromptExperimentResponse(BaseModel):
    mode: str
    description: str
    messages: Optional[List[Dict[str, str]]] = None
    data: Optional[Any] = None
