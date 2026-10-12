"""FastAPI route handlers for LLM chat completions."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.models.llm import ChatRequest, ChatResponse
from app.models.prompts import (
    PromptExperimentMode,
    PromptExperimentRequest,
    PromptExperimentResponse,
)
from app.services.llm import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    llm_service,
)
from app.services.prompt_service import (
    build_grounded_messages,
    build_json_constraint_messages,
    build_system_user_messages,
    compare_vague_and_specific_prompts,
    run_grounded_query,
    run_json_constraint_experiment,
    run_system_user_experiment,
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


@router.post(
    "/prompt-experiment",
    response_model=PromptExperimentResponse,
    summary="Run a prompt engineering experiment",
    description=(
        "Executes a prompt experiment demonstrating system/user roles, "
        "vague vs specific prompt comparisons, explicit JSON constraints, "
        "or ChronoLex regulatory grounding."
    ),
)
def run_prompt_experiment(request: PromptExperimentRequest) -> PromptExperimentResponse:
    """Endpoint for prompt engineering experiments."""
    try:
        if request.mode == PromptExperimentMode.SYSTEM_USER:
            messages = build_system_user_messages(user_prompt=request.user_prompt)
            data = run_system_user_experiment(user_prompt=request.user_prompt)
            return PromptExperimentResponse(
                mode="system_user",
                description="Demonstrates distinct separation of system persona/constraints and user task.",
                messages=messages,
                data=data,
            )

        elif request.mode == PromptExperimentMode.COMPARE:
            prompts = [request.user_prompt, "In one sentence, state the refund window in days."] if request.user_prompt else None
            comparison = compare_vague_and_specific_prompts(prompts=prompts)
            return PromptExperimentResponse(
                mode="compare",
                description="Demonstrates comparison between vague and specific prompts run independently.",
                messages=None,
                data=comparison,
            )

        elif request.mode == PromptExperimentMode.JSON:
            messages = build_json_constraint_messages(request.user_prompt)
            data = run_json_constraint_experiment(user_prompt=request.user_prompt)
            return PromptExperimentResponse(
                mode="json",
                description="Demonstrates explicit JSON output constraint and safe parsing.",
                messages=messages,
                data=data,
            )

        elif request.mode == PromptExperimentMode.GROUNDING:
            if not request.question or not request.question.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Question is required for grounding mode.",
                )
            context = request.context or ""
            messages = build_grounded_messages(request.question, context)
            data = run_grounded_query(question=request.question, context=context)
            return PromptExperimentResponse(
                mode="grounding",
                description="Demonstrates ChronoLex regulatory grounding prompt with context delimiters and anti-injection instructions.",
                messages=messages,
                data=data,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported mode: {request.mode}",
        )

    except HTTPException:
        raise

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
        logger.exception("Unexpected error in prompt-experiment endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during prompt experimentation.",
        ) from e
