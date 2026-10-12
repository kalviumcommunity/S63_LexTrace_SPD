"""FastAPI route handlers for LLM chat completions."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.models.llm import ChatRequest, ChatResponse
from app.services.llm import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    llm_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a chat completion request",
    description="Sends a user prompt to an OpenAI-compatible LLM provider and returns the answer and token usage.",
)
def chat_completion(request: ChatRequest) -> ChatResponse:
    """Endpoint for chat completions with robust error mapping."""
    try:
        response = llm_service.send_chat_completion(
            user_message=request.message,
            system_prompt=request.system_prompt,
        )
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except LLMConfigurationError as e:
        logger.error("LLM configuration error: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        ) from e

    except LLMAuthenticationError as e:
        logger.error("LLM authentication failure: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e

    except LLMRateLimitError as e:
        logger.warning("LLM rate limit reached: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
        ) from e

    except LLMConnectionError as e:
        logger.error("LLM connection error: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message,
        ) from e

    except LLMProviderError as e:
        logger.error("LLM provider error: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message,
        ) from e

    except Exception as e:
        logger.exception("Unexpected error in chat_completion endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred while processing the LLM request.",
        ) from e
