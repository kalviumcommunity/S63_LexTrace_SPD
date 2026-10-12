from pydantic import BaseModel, Field, field_validator


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to send to the LLM.")
    system_prompt: str | None = Field(
        default=None,
        description="Optional system prompt to guide LLM behavior.",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("User message cannot be empty.")
        return v.strip()


class ChatResponse(BaseModel):
    answer: str
    model: str
    usage: TokenUsage | None = None
