from typing import Dict, List, Literal

from pydantic import BaseModel, Field, field_validator


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float | None = Field(default=None)


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to send to the LLM.")
    system_prompt: str | None = Field(
        default=None,
        description="Optional system prompt to guide LLM behavior.",
    )
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Prior conversation messages, including optional system context.",
    )
    retrieved_context: str | None = Field(
        default=None,
        description="Optional retrieved evidence included in the current user turn.",
    )
    context_limit: int = Field(default=8192, gt=0)
    reserved_output_tokens: int = Field(default=1000, ge=0)
    safety_margin_tokens: int = Field(default=200, ge=0)
    history_strategy: Literal["trim", "summarize"] = "trim"

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("User message cannot be empty.")
        return v.strip()

    @field_validator("conversation_history")
    @classmethod
    def validate_history(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        for message in v:
            if message.get("role") not in {"system", "user", "assistant"}:
                raise ValueError("Conversation history roles must be system, user, or assistant.")
            if not message.get("content", "").strip():
                raise ValueError("Conversation history message content cannot be empty.")
        return v


class ChatResponse(BaseModel):
    answer: str
    model: str
    usage: TokenUsage | None = None
    conversation_history: List[Dict[str, str]] | None = None
    context_management: Dict[str, int | bool | str] | None = None
