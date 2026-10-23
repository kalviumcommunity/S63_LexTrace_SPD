"""Tokenization, token counting, cost estimation, and context budgeting utilities.

Provides:
- Token counting for strings, batches, and UTF-8 text files using tiktoken.
- Illustrative API cost estimation with strict non-negative validation.
- Context-window budgeting with component breakdowns and margin safeguards.
- Corpus-scale extrapolation for collections (e.g., 4,000 regulatory documents).
"""

from functools import lru_cache
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import tiktoken

from app.models.tokens import (
    ContextBudgetResponse,
    ContextComponentBreakdown,
    CorpusScaleEstimate,
    CostEstimateResponse,
)

logger = logging.getLogger(__name__)

# Illustrative default rates (USD per 1,000 tokens)
DEFAULT_INPUT_PRICE_PER_1K: float = 0.0005
DEFAULT_OUTPUT_PRICE_PER_1K: float = 0.0015
DEFAULT_ENCODING: str = "cl100k_base"


# ---------------------------------------------------------------------------
# 1. Tokenizer Access & Token Counting
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def get_tokenizer(encoding_name: str = DEFAULT_ENCODING) -> tiktoken.Encoding:
    """Retrieves and caches a tiktoken encoding instance."""
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception as exc:
        raise ValueError(
            f"Invalid or unsupported tokenizer encoding '{encoding_name}'. "
            f"Supported encodings include 'cl100k_base', 'p50k_base', 'r50k_base'."
        ) from exc


def count_tokens(text: Optional[str], encoding_name: str = DEFAULT_ENCODING) -> int:
    """Counts tokens in a string using the specified encoding.

    Empty or None strings return 0 tokens.
    """
    if not text:
        return 0
    enc = get_tokenizer(encoding_name)
    return len(enc.encode(text))


def count_tokens_batch(
    texts: List[str],
    encoding_name: str = DEFAULT_ENCODING,
) -> List[int]:
    """Returns a list of token counts corresponding to each text in the input list."""
    enc = get_tokenizer(encoding_name)
    return [len(enc.encode(t)) if t else 0 for t in texts]


def count_tokens_in_file(
    file_path: Union[str, Path],
    encoding_name: str = DEFAULT_ENCODING,
) -> int:
    """Reads a UTF-8 text file and counts its tokens.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the path points to a directory or is not readable.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {path}")

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as err:
        raise ValueError(f"File at {path} could not be decoded as UTF-8: {err}") from err

    return count_tokens(content, encoding_name=encoding_name)


def inspect_policy_file(
    repo_root: Optional[Path] = None,
    encoding_name: str = DEFAULT_ENCODING,
) -> Dict[str, Any]:
    """Inspects 'data/policy.txt' if present in the repository, returning token count or guidance."""
    root = repo_root or Path(__file__).resolve().parent.parent.parent.parent
    policy_path = root / "data" / "policy.txt"

    if policy_path.exists() and policy_path.is_file():
        tokens = count_tokens_in_file(policy_path, encoding_name=encoding_name)
        return {
            "exists": True,
            "path": str(policy_path),
            "token_count": tokens,
            "message": f"Successfully counted {tokens} tokens in {policy_path.name}.",
        }

    return {
        "exists": False,
        "path": str(policy_path),
        "token_count": 0,
        "message": (
            "File 'data/policy.txt' was not found. To evaluate local documents, "
            "place a UTF-8 encoded text file at 'data/policy.txt' or specify a file path."
        ),
    }


# ---------------------------------------------------------------------------
# 2. API Cost Estimation
# ---------------------------------------------------------------------------


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_1k: float = DEFAULT_INPUT_PRICE_PER_1K,
    output_price_per_1k: float = DEFAULT_OUTPUT_PRICE_PER_1K,
) -> CostEstimateResponse:
    """Calculates estimated API cost from input and output token counts.

    Formula:
        cost = (input_tokens / 1000 * input_price_per_1k) + (output_tokens / 1000 * output_price_per_1k)

    Raises:
        ValueError: If token counts or price rates are negative.
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts must be non-negative integers.")
    if input_price_per_1k < 0.0 or output_price_per_1k < 0.0:
        raise ValueError("Price rates per 1,000 tokens must be non-negative.")

    total_tokens = input_tokens + output_tokens
    input_cost = (input_tokens / 1000.0) * input_price_per_1k
    output_cost = (output_tokens / 1000.0) * output_price_per_1k
    total_cost = input_cost + output_cost

    return CostEstimateResponse(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_price_per_1k=input_price_per_1k,
        output_price_per_1k=output_price_per_1k,
        input_cost=round(input_cost, 8),
        output_cost=round(output_cost, 8),
        total_cost=round(total_cost, 8),
        formatted_input_cost=f"${input_cost:.6f}",
        formatted_output_cost=f"${output_cost:.6f}",
        formatted_total_cost=f"${total_cost:.6f}",
        is_illustrative_rate=True,
    )


# ---------------------------------------------------------------------------
# 3. Context-Window Budgeting
# ---------------------------------------------------------------------------


def estimate_context_budget(
    system_prompt: str = "",
    user_question: str = "",
    retrieved_context: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    reserved_output_tokens: int = 1000,
    safety_margin_tokens: int = 200,
    context_limit: int = 8192,
    encoding_name: str = DEFAULT_ENCODING,
) -> ContextBudgetResponse:
    """Estimates whether an assembled prompt fits within a configured context window budget.

    Accounts for system prompt, user question, retrieved regulatory evidence,
    optional conversation history, reserved output generation, and a safety margin.
    """
    if context_limit <= 0:
        raise ValueError("context_limit must be a positive integer.")
    if reserved_output_tokens < 0 or safety_margin_tokens < 0:
        raise ValueError("Reserved output tokens and safety margin must be non-negative.")

    sys_tokens = count_tokens(system_prompt, encoding_name)
    q_tokens = count_tokens(user_question, encoding_name)
    ctx_tokens = count_tokens(retrieved_context, encoding_name)

    hist_tokens = 0
    if conversation_history:
        for turn in conversation_history:
            hist_tokens += count_tokens(turn.get("content", ""), encoding_name)

    total_input_tokens = sys_tokens + q_tokens + ctx_tokens + hist_tokens
    total_demanded_tokens = total_input_tokens + reserved_output_tokens + safety_margin_tokens
    remaining_capacity = context_limit - total_demanded_tokens
    fits_budget = total_demanded_tokens <= context_limit

    breakdown = ContextComponentBreakdown(
        system_tokens=sys_tokens,
        question_tokens=q_tokens,
        context_tokens=ctx_tokens,
        history_tokens=hist_tokens,
        total_input_tokens=total_input_tokens,
        reserved_output_tokens=reserved_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
        total_demanded_tokens=total_demanded_tokens,
    )

    if fits_budget:
        msg = f"Request fits within budget with {remaining_capacity} remaining tokens."
    else:
        overage = total_demanded_tokens - context_limit
        msg = f"Request exceeds context budget by {overage} tokens. Reduce context size or chunk count."

    return ContextBudgetResponse(
        context_limit=context_limit,
        breakdown=breakdown,
        remaining_capacity=remaining_capacity,
        fits_budget=fits_budget,
        status_message=msg,
    )


# ---------------------------------------------------------------------------
# 4. Corpus-Scale Extrapolation (e.g. 4,000 Documents)
# ---------------------------------------------------------------------------


def estimate_corpus_scale(
    document_token_counts: List[int],
    target_document_count: int = 4000,
    input_price_per_1k: float = DEFAULT_INPUT_PRICE_PER_1K,
) -> CorpusScaleEstimate:
    """Calculates corpus summary statistics and extrapolates token volume and costs to 4,000 documents."""
    if target_document_count < 0:
        raise ValueError("target_document_count must be non-negative.")
    if input_price_per_1k < 0.0:
        raise ValueError("input_price_per_1k must be non-negative.")

    valid_counts = [c for c in document_token_counts if c >= 0]
    doc_count = len(valid_counts)

    if doc_count == 0:
        return CorpusScaleEstimate(
            document_count=0,
            total_tokens=0,
            avg_tokens_per_doc=0.0,
            min_tokens_per_doc=0,
            max_tokens_per_doc=0,
            target_scale_documents=target_document_count,
            projected_corpus_tokens=0,
            estimated_chat_input_cost=0.0,
            formatted_estimated_cost="$0.000000",
            input_price_per_1k=input_price_per_1k,
        )

    total_tokens = sum(valid_counts)
    avg_tokens = total_tokens / doc_count
    min_tokens = min(valid_counts)
    max_tokens = max(valid_counts)

    projected_tokens = int(round(avg_tokens * target_document_count))
    projected_cost = (projected_tokens / 1000.0) * input_price_per_1k

    return CorpusScaleEstimate(
        document_count=doc_count,
        total_tokens=total_tokens,
        avg_tokens_per_doc=round(avg_tokens, 2),
        min_tokens_per_doc=min_tokens,
        max_tokens_per_doc=max_tokens,
        target_scale_documents=target_document_count,
        projected_corpus_tokens=projected_tokens,
        estimated_chat_input_cost=round(projected_cost, 6),
        formatted_estimated_cost=f"${projected_cost:.6f}",
        input_price_per_1k=input_price_per_1k,
    )


def count_tokens_in_directory(
    directory_path: Union[str, Path],
    encoding_name: str = DEFAULT_ENCODING,
) -> List[Tuple[str, int]]:
    """Scans all .txt files in a directory and returns a list of (filename, token_count) tuples."""
    dir_path = Path(directory_path).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    results: List[Tuple[str, int]] = []
    for file_path in sorted(dir_path.glob("*.txt")):
        if file_path.is_file():
            try:
                count = count_tokens_in_file(file_path, encoding_name=encoding_name)
                results.append((file_path.name, count))
            except Exception as e:
                logger.warning("Could not read file %s: %s", file_path, e)
    return results


def token_chunks(
    text: Optional[str],
    size: int = 400,
    overlap: int = 60,
    encoding: str = DEFAULT_ENCODING,
) -> List[str]:
    """Splits text into token-sized chunks with controlled token overlap.

    Re-exports app.utils.chunking.token_chunks for convenient direct access.
    """
    from app.utils.chunking import token_chunks as _token_chunks

    return _token_chunks(text=text, size=size, overlap=overlap, encoding=encoding)
