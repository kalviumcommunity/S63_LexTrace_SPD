"""FastAPI route handlers for LLM chat completions."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.models.llm import ChatRequest, ChatResponse
from app.models.prompts import (
    PromptExperimentMode,
    PromptExperimentRequest,
    PromptExperimentResponse,
)
from app.models.structured import (
    StructuredRequest,
    StructuredResponse,
)
from app.models.document import (
    ChunkRequest,
    ChunkResponse,
)
from app.models.tokens import (
    ContextBudgetRequest,
    ContextBudgetResponse,
    CostEstimateRequest,
    CostEstimateResponse,
    TokenEstimateCombinedRequest,
    TokenEstimateCombinedResponse,
)
from app.services.llm import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    llm_service,
)
from app.services.structured_service import (
    StructuredOutputError,
    request_structured_completion,
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
from app.utils.chunking import token_chunks_detailed
from app.utils.tokenization import (
    calculate_cost,
    count_tokens,
    estimate_context_budget,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    response_model_exclude_none=True,
    summary="Send a chat completion request",
    description="Sends a user prompt to an OpenAI-compatible LLM provider and returns the answer and token usage.",
)
def chat_completion(request: ChatRequest) -> ChatResponse:
    """Endpoint for chat completions with robust error mapping."""
    try:
        response = llm_service.send_chat_completion(
            user_message=request.message,
            system_prompt=request.system_prompt,
            conversation_history=request.conversation_history,
            retrieved_context=request.retrieved_context,
            context_limit=request.context_limit,
            reserved_output_tokens=request.reserved_output_tokens,
            safety_margin_tokens=request.safety_margin_tokens,
            history_strategy=request.history_strategy,
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


@router.post(
    "/token-estimate",
    response_model=TokenEstimateCombinedResponse,
    summary="Estimate token counts, API cost, and context budget",
    description=(
        "Calculates token counts for text, computes estimated API pricing for input/output tokens, "
        "and checks context window budgeting against model limits."
    ),
)
def estimate_tokens_endpoint(
    request: TokenEstimateCombinedRequest,
) -> TokenEstimateCombinedResponse:
    """Endpoint for token counting, cost estimation, and context budgeting."""
    try:
        token_count: Optional[int] = None
        text_length_chars: Optional[int] = None
        if request.text is not None:
            token_count = count_tokens(request.text, encoding_name=request.encoding)
            text_length_chars = len(request.text)

        cost_est = None
        if request.cost_params is not None:
            cost_est = calculate_cost(
                input_tokens=request.cost_params.input_tokens,
                output_tokens=request.cost_params.output_tokens,
                input_price_per_1k=request.cost_params.input_price_per_1k,
                output_price_per_1k=request.cost_params.output_price_per_1k,
            )

        budget_est = None
        if request.budget_params is not None:
            budget_est = estimate_context_budget(
                system_prompt=request.budget_params.system_prompt,
                user_question=request.budget_params.user_question,
                retrieved_context=request.budget_params.retrieved_context,
                conversation_history=request.budget_params.conversation_history,
                reserved_output_tokens=request.budget_params.reserved_output_tokens,
                safety_margin_tokens=request.budget_params.safety_margin_tokens,
                context_limit=request.budget_params.context_limit,
                encoding_name=request.budget_params.encoding or request.encoding,
            )

        return TokenEstimateCombinedResponse(
            encoding=request.encoding,
            token_count=token_count,
            text_length_chars=text_length_chars,
            cost_estimate=cost_est,
            budget_estimate=budget_est,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in token-estimate endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during token estimation: {e}",
        ) from e


@router.post(
    "/chunk",
    response_model=ChunkResponse,
    response_model_exclude_none=True,
    summary="Token-aware document chunking",
    description="Splits input text into token-bounded chunks with controlled token overlap.",
)
def chunk_text_endpoint(request: ChunkRequest) -> ChunkResponse:
    """Chunks text into token-bounded slices with controlled overlap."""
    text_to_process = request.text
    if request.clean_first and text_to_process.strip():
        from app.utils.text_cleaning import clean_text

        text_to_process = clean_text(text_to_process)

    try:
        detailed = token_chunks_detailed(
            text=text_to_process,
            size=request.chunk_size,
            overlap=request.chunk_overlap,
            encoding=request.encoding_name,
        )
        total_chunks = len(detailed)
        total_tokens = sum(c["token_count"] for c in detailed)
        chunks = [c["text"] for c in detailed]

        return ChunkResponse(
            total_chunks=total_chunks,
            total_tokens=total_tokens,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            encoding_name=request.encoding_name,
            chunks=chunks,
            chunk_details=detailed,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in chunk endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during chunking: {e}",
        ) from e


@router.post(
    "/structured",
    response_model=StructuredResponse,
    response_model_exclude_none=True,
    summary="Request structured JSON response",
    description=(
        "Requests a strictly structured JSON response containing 'answer' and 'source' keys. "
        "Applies deterministic sampling (temperature=0), JSON mode when supported, "
        "Pydantic schema validation, and safe bounded error recovery (at most one retry). "
        "Note: In educational demonstration mode, the 'source' field represents model attribution, "
        "not verified retrieval evidence."
    ),
)
def structured_completion_endpoint(request: StructuredRequest) -> StructuredResponse:
    """Endpoint for structured JSON output with validation and error recovery."""
    try:
        validated_obj, chat_resp, retries = request_structured_completion(
            question=request.question,
            system_prompt=request.system_prompt,
            temperature=request.temperature if request.temperature is not None else 0.0,
            use_json_mode=request.use_json_mode,
        )

        return StructuredResponse(
            answer=validated_obj.answer,
            source=validated_obj.source,
            model=chat_resp.model,
            usage=chat_resp.usage,
            retries=retries,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except StructuredOutputError as e:
        logger.error("Structured output validation failure: %s", e.message)
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail={
                "error": "Structured output validation failed",
                "message": e.message,
                "validation_error": e.validation_error,
                "retries": e.retries,
            },
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
        logger.exception("Unexpected error in structured completion endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred while processing the structured request.",
        ) from e
