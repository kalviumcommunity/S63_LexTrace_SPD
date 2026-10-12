"""Reusable LLM service module for OpenAI-compatible chat completions.

Handles client initialization, message construction, response parsing,
token usage tracking, safe logging, and explicit error handling with backoff.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from app.core.config import settings
from app.models.llm import ChatResponse, TokenUsage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Service Exceptions
# ---------------------------------------------------------------------------


class LLMServiceError(Exception):
    """Base exception for all LLM service-level errors."""

    def __init__(self, message: str, status_code: int = 500, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


class LLMConfigurationError(LLMServiceError):
    """Raised when required configuration (e.g., API key) is missing."""

    def __init__(
        self,
        message: str = (
            "Configuration error: OPENAI_API_KEY is not configured. "
            "Please set OPENAI_API_KEY in your environment or .env file."
        ),
    ):
        super().__init__(message, status_code=500, retryable=False)


class LLMAuthenticationError(LLMServiceError):
    """Raised when authentication with the LLM provider fails (HTTP 401)."""

    def __init__(
        self,
        message: str = "Authentication failed (401): Check OPENAI_API_KEY and provider credentials.",
    ):
        super().__init__(message, status_code=401, retryable=False)


class LLMRateLimitError(LLMServiceError):
    """Raised when rate limits or quotas are exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limited (429): Check provider rate limits or quota and retry appropriately.",
    ):
        super().__init__(message, status_code=429, retryable=False)


class LLMConnectionError(LLMServiceError):
    """Raised when connection to provider fails or times out."""

    def __init__(
        self,
        message: str = "Connection error: Unable to reach the LLM provider. Please check your network and provider endpoint.",
    ):
        super().__init__(message, status_code=502, retryable=True)


class LLMProviderError(LLMServiceError):
    """Raised on general unexpected LLM provider errors."""

    def __init__(
        self,
        message: str = "Provider error: The LLM provider encountered an error while processing the request.",
        status_code: int = 502,
    ):
        super().__init__(message, status_code=status_code, retryable=False)


# ---------------------------------------------------------------------------
# Client Factory
# ---------------------------------------------------------------------------


def get_llm_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> OpenAI:
    """Initialize and return an OpenAI-compatible client.

    Validates that API key configuration is present before instantiating.
    """
    key = api_key if api_key is not None else settings.OPENAI_API_KEY
    url = base_url if base_url is not None else settings.OPENAI_BASE_URL

    if not key or not str(key).strip():
        raise LLMConfigurationError()

    return OpenAI(
        api_key=key.strip(),
        base_url=url.strip() if url else None,
    )


# ---------------------------------------------------------------------------
# Reusable LLM Service
# ---------------------------------------------------------------------------


class LLMService:
    """Service encapsulating OpenAI-compatible chat completion requests."""

    def __init__(
        self,
        client: Optional[OpenAI] = None,
        default_model: Optional[str] = None,
        max_retries: int = 2,
        initial_backoff: float = 0.5,
    ):
        self._client = client
        self.default_model = default_model
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    def get_client(self) -> OpenAI:
        """Returns the configured client or initializes a new one."""
        if self._client is not None:
            return self._client
        return get_llm_client()

    def send_messages(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        client: Optional[OpenAI] = None,
    ) -> ChatResponse:
        """Sends an arbitrary structured message list to an OpenAI-compatible API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            model: Optional model identifier. Defaults to configured CHAT_MODEL.
            client: Optional pre-configured OpenAI client (useful for testing or dependency injection).

        Returns:
            ChatResponse containing the generated answer, model name, and token usage.
        """
        if not messages:
            raise ValueError("Messages list cannot be empty.")

        selected_model = model or self.default_model or settings.CHAT_MODEL

        # Log request messages (Never log credentials or auth headers)
        logger.info("REQUEST: %s", messages)

        active_client = client or self._client or get_llm_client()

        attempt = 0
        while True:
            try:
                raw_response = active_client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                )

                # Safe content extraction
                answer = ""
                if raw_response and getattr(raw_response, "choices", None):
                    first_choice = raw_response.choices[0]
                    if getattr(first_choice, "message", None):
                        answer = getattr(first_choice.message, "content", "") or ""

                # Token usage extraction
                usage_info: Optional[TokenUsage] = None
                raw_usage = getattr(raw_response, "usage", None)
                if raw_usage is not None:
                    usage_info = TokenUsage(
                        prompt_tokens=getattr(raw_usage, "prompt_tokens", 0) or 0,
                        completion_tokens=getattr(raw_usage, "completion_tokens", 0) or 0,
                        total_tokens=getattr(raw_usage, "total_tokens", 0) or 0,
                    )

                response_model = getattr(raw_response, "model", None) or selected_model

                # Log response content and token usage
                logger.info("RESPONSE: %s", answer)
                logger.info("USAGE: %s", raw_usage)

                return ChatResponse(
                    answer=answer,
                    model=response_model,
                    usage=usage_info,
                )

            except AuthenticationError as e:
                err_msg = "Authentication failed (401): Check OPENAI_API_KEY and provider credentials."
                logger.error("LLM Authentication error: %s", err_msg)
                raise LLMAuthenticationError(err_msg) from e

            except RateLimitError as e:
                err_str = str(e).lower()
                is_quota_exhausted = "quota" in err_str or "insufficient_quota" in err_str

                if not is_quota_exhausted and attempt < self.max_retries:
                    attempt += 1
                    backoff = min(self.initial_backoff * (2 ** (attempt - 1)), 4.0)
                    logger.warning(
                        "Rate limit encountered. Retrying in %.2fs (attempt %d/%d)...",
                        backoff,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(backoff)
                    continue

                err_msg = "Rate limited (429): Check provider rate limits or quota and retry appropriately."
                logger.error("LLM Rate limit error: %s", err_msg)
                raise LLMRateLimitError(err_msg) from e

            except (APIConnectionError, APITimeoutError) as e:
                if attempt < self.max_retries:
                    attempt += 1
                    backoff = min(self.initial_backoff * (2 ** (attempt - 1)), 4.0)
                    logger.warning(
                        "LLM connection error/timeout. Retrying in %.2fs (attempt %d/%d)...",
                        backoff,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(backoff)
                    continue

                err_msg = "Connection error: Unable to reach the LLM provider. Please check your network and provider endpoint."
                logger.error("LLM Connection failure: %s", err_msg)
                raise LLMConnectionError(err_msg) from e

            except APIStatusError as e:
                err_msg = f"LLM provider error ({e.status_code}): {e.message}"
                logger.error("LLM API status error: %s", err_msg)
                raise LLMProviderError(err_msg, status_code=e.status_code if e.status_code in (400, 403, 404, 502, 503, 504) else 502) from e

            except OpenAIError as e:
                err_msg = f"LLM provider error: {str(e)}"
                logger.error("LLM generic error: %s", err_msg)
                raise LLMProviderError(err_msg) from e

    def send_chat_completion(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[OpenAI] = None,
    ) -> ChatResponse:
        """Sends a chat completion request to an OpenAI-compatible API.

        Args:
            user_message: The prompt provided by the user.
            system_prompt: Optional system instruction. Defaults to 'You are a concise assistant.'
            model: Optional model identifier. Defaults to configured CHAT_MODEL.
            client: Optional pre-configured OpenAI client (useful for testing or dependency injection).

        Returns:
            ChatResponse containing the generated answer, model name, and token usage.
        """
        if not user_message or not user_message.strip():
            raise ValueError("User message cannot be empty.")

        sys_instruction = system_prompt or "You are a concise assistant."

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": sys_instruction},
            {"role": "user", "content": user_message.strip()},
        ]

        return self.send_messages(messages=messages, model=model, client=client)


# Singleton service instance for application-wide use
llm_service = LLMService()
