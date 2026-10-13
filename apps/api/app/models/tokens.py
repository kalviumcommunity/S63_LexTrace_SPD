"""Pydantic models for tokenization, cost estimation, and context budgeting."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TokenCountRequest(BaseModel):
    text: str = Field(..., description="Text content to tokenize and count.")
    encoding: str = Field(
        default="cl100k_base",
        description="Tokenizer encoding identifier (default: cl100k_base).",
    )


class TokenCountResponse(BaseModel):
    text_length_chars: int
    token_count: int
    encoding: str


class CostEstimateRequest(BaseModel):
    input_tokens: int = Field(default=0, ge=0, description="Count of prompt/input tokens.")
    output_tokens: int = Field(default=0, ge=0, description="Count of completion/output tokens.")
    input_price_per_1k: float = Field(
        default=0.0005,
        ge=0.0,
        description="Illustrative input price per 1,000 tokens (USD).",
    )
    output_price_per_1k: float = Field(
        default=0.0015,
        ge=0.0,
        description="Illustrative output price per 1,000 tokens (USD).",
    )


class CostEstimateResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_price_per_1k: float
    output_price_per_1k: float
    input_cost: float
    output_cost: float
    total_cost: float
    formatted_input_cost: str
    formatted_output_cost: str
    formatted_total_cost: str
    is_illustrative_rate: bool = True


class ContextBudgetRequest(BaseModel):
    system_prompt: str = Field(default="", description="System instruction text.")
    user_question: str = Field(default="", description="User prompt text.")
    retrieved_context: str = Field(default="", description="Retrieved regulatory context.")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Optional prior conversation turns.",
    )
    reserved_output_tokens: int = Field(
        default=1000,
        ge=0,
        description="Tokens reserved for model completion generation.",
    )
    safety_margin_tokens: int = Field(
        default=200,
        ge=0,
        description="Safety buffer tokens for formatting/overhead.",
    )
    context_limit: int = Field(
        default=8192,
        gt=0,
        description="Configured context window limit in tokens.",
    )
    encoding: str = Field(
        default="cl100k_base",
        description="Tokenizer encoding identifier.",
    )


class ContextComponentBreakdown(BaseModel):
    system_tokens: int
    question_tokens: int
    context_tokens: int
    history_tokens: int
    total_input_tokens: int
    reserved_output_tokens: int
    safety_margin_tokens: int
    total_demanded_tokens: int


class ContextBudgetResponse(BaseModel):
    context_limit: int
    breakdown: ContextComponentBreakdown
    remaining_capacity: int
    fits_budget: bool
    status_message: str


class CorpusScaleEstimate(BaseModel):
    document_count: int
    total_tokens: int
    avg_tokens_per_doc: float
    min_tokens_per_doc: int
    max_tokens_per_doc: int
    target_scale_documents: int
    projected_corpus_tokens: int
    estimated_chat_input_cost: float
    formatted_estimated_cost: str
    input_price_per_1k: float


class TokenEstimateCombinedRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Optional text to count tokens for.")
    encoding: str = Field(default="cl100k_base", description="Tokenizer encoding identifier.")
    cost_params: Optional[CostEstimateRequest] = Field(
        default=None,
        description="Optional cost estimation parameters.",
    )
    budget_params: Optional[ContextBudgetRequest] = Field(
        default=None,
        description="Optional context budget parameters.",
    )


class TokenEstimateCombinedResponse(BaseModel):
    encoding: str
    token_count: Optional[int] = None
    text_length_chars: Optional[int] = None
    cost_estimate: Optional[CostEstimateResponse] = None
    budget_estimate: Optional[ContextBudgetResponse] = None
