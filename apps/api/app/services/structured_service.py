"""Structured output service for ChronoLex.

Handles requesting strictly formatted JSON output from OpenAI-compatible LLMs,
parsing with Python's json.loads, validating with Pydantic schemas,
and providing safe, bounded (single-attempt) error recovery.
"""

import logging
from typing import Any, Optional, Tuple, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.models.llm import ChatResponse
from app.models.structured import StructuredAnswer
from app.services.llm import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMServiceError,
    llm_service,
)
from app.utils.json_parsing import parse_and_validate

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_STRUCTURED_SYSTEM_PROMPT = (
    'Reply with ONLY a JSON object containing the keys "answer" and "source". '
    "Do not include any additional prose."
)


class StructuredOutputError(LLMServiceError):
    """Raised when the LLM output fails JSON parsing or schema validation after bounded retries."""

    def __init__(
        self,
        message: str = "Model output failed structured JSON parsing and validation.",
        raw_response: Optional[str] = None,
        validation_error: Optional[str] = None,
        retries: int = 1,
        status_code: int = 422,
    ):
        super().__init__(message, status_code=status_code, retryable=False)
        self.raw_response = raw_response
        self.validation_error = validation_error
        self.retries = retries


def request_structured_completion(
    question: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    schema: Type[T] = StructuredAnswer,
    temperature: float = 0.0,
    use_json_mode: bool = True,
    client: Optional[OpenAI] = None,
    service: Optional[Any] = None,
    input_price_per_1k: Optional[float] = None,
    output_price_per_1k: Optional[float] = None,
) -> Tuple[T, ChatResponse, int]:
    """Requests a structured JSON response from an LLM with bounded error recovery.

    Workflow:
    1. Sends system and user prompt with temperature=0 and JSON response_format (if supported).
    2. Safely parses returned text with json.loads() and validates JSON object constraint.
    3. Validates field presence, types, and non-empty constraints via Pydantic.
    4. If parsing or validation fails, retries at most once with a reminder prompt.
    5. If retry also fails, raises a structured StructuredOutputError without exposing internal stack traces.

    Permanent errors (authentication, configuration) fail immediately without retrying.

    Args:
        question: User query string.
        system_prompt: Optional system instruction overriding the default.
        model: Optional model identifier.
        schema: Pydantic model class for schema validation (defaults to StructuredAnswer).
        temperature: Sampling temperature (defaults to 0.0 for deterministic JSON).
        use_json_mode: Whether to request json_object response format when supported.
        client: Optional preconfigured OpenAI client.
        service: Optional LLMService instance.
        input_price_per_1k: Optional pricing parameter for input tokens.
        output_price_per_1k: Optional pricing parameter for completion tokens.

    Returns:
        Tuple of (validated_schema_model, chat_response, retries_count).

    Raises:
        ValueError: If question is empty or invalid.
        LLMAuthenticationError: On 401 provider failures (no retry).
        LLMConfigurationError: On missing configuration (no retry).
        StructuredOutputError: If output cannot be validated after bounded retry.
    """
    if not question or not str(question).strip():
        raise ValueError("Question cannot be empty.")

    active_service = service or llm_service
    selected_model = model or active_service.default_model or settings.CHAT_MODEL

    sys_instruction = (
        system_prompt.strip()
        if system_prompt and system_prompt.strip()
        else DEFAULT_STRUCTURED_SYSTEM_PROMPT
    )
    user_prompt = question.strip()

    messages = [
        {"role": "system", "content": sys_instruction},
        {"role": "user", "content": user_prompt},
    ]

    response_format = {"type": "json_object"} if use_json_mode else None

    logger.info(
        "REQUEST MODE: structured_json | Model: %s | Temperature: %s | JSON Mode: %s",
        selected_model,
        temperature,
        use_json_mode,
    )

    # Attempt 1: Initial structured completion request
    initial_response = active_service.send_messages(
        messages=messages,
        model=selected_model,
        client=client,
        input_price_per_1k=input_price_per_1k,
        output_price_per_1k=output_price_per_1k,
        temperature=temperature,
        response_format=response_format,
    )

    raw_content = initial_response.answer
    validated, parse_err = parse_and_validate(raw_content, schema=schema)

    if validated is not None:
        logger.info(
            "Structured JSON parsing and validation succeeded on initial attempt (0 retries). "
            "Model: %s | Usage: %s",
            initial_response.model,
            initial_response.usage,
        )
        return validated, initial_response, 0

    # Initial attempt failed: log and execute bounded single retry
    logger.warning(
        "Structured JSON validation failed on initial attempt: %s. Initiating bounded retry (1/1)...",
        parse_err,
    )

    required_fields = list(schema.model_fields.keys())
    retry_messages = [
        {"role": "system", "content": sys_instruction},
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": raw_content or ""},
        {
            "role": "user",
            "content": (
                f"Your previous response failed validation: {parse_err}. "
                f"Please reply with ONLY a valid JSON object containing the required keys {required_fields}. "
                "Do not include any additional prose or markdown code blocks."
            ),
        },
    ]

    retry_response = active_service.send_messages(
        messages=retry_messages,
        model=selected_model,
        client=client,
        input_price_per_1k=input_price_per_1k,
        output_price_per_1k=output_price_per_1k,
        temperature=temperature,
        response_format=response_format,
    )

    retry_raw = retry_response.answer
    retry_validated, retry_err = parse_and_validate(retry_raw, schema=schema)

    if retry_validated is not None:
        logger.info(
            "Structured JSON parsing and validation succeeded on retry attempt 1. "
            "Model: %s | Usage: %s",
            retry_response.model,
            retry_response.usage,
        )
        return retry_validated, retry_response, 1

    # Both attempts failed: log and return structured error
    logger.error(
        "Structured JSON validation failed after bounded retry: %s",
        retry_err,
    )
    raise StructuredOutputError(
        message=f"Model output failed structured JSON validation after 1 retry: {retry_err}",
        raw_response=retry_raw,
        validation_error=retry_err,
        retries=1,
    )
