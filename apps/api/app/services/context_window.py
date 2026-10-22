"""Token-aware conversation history management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from app.utils.tokenization import count_tokens

Message = Dict[str, str]


@dataclass(frozen=True)
class HistoryManagementResult:
    """Managed messages and accounting details for one model request."""

    messages: List[Message]
    input_tokens: int
    budget: int
    removed_messages: int = 0
    summarized_messages: int = 0
    summary_message: Optional[Message] = None

    @property
    def fits_budget(self) -> bool:
        return self.input_tokens <= self.budget


def count_message_tokens(messages: List[Message], encoding_name: str = "cl100k_base") -> int:
    """Count message content tokens, excluding provider-specific message overhead."""
    return sum(count_tokens(message.get("content", ""), encoding_name) for message in messages)


def _history_budget(
    context_limit: int,
    reserved_output_tokens: int,
    safety_margin_tokens: int,
) -> int:
    if context_limit <= 0:
        raise ValueError("context_limit must be a positive integer.")
    if reserved_output_tokens < 0 or safety_margin_tokens < 0:
        raise ValueError("Reserved output tokens and safety margin must be non-negative.")

    budget = context_limit - reserved_output_tokens - safety_margin_tokens
    if budget <= 0:
        raise ValueError(
            "context_limit must leave room for input after reserved output and safety margin."
        )
    return budget


def trim_messages(
    messages: List[Message],
    budget: int,
    encoding_name: str = "cl100k_base",
) -> HistoryManagementResult:
    """Drop oldest non-system messages until the input fits the budget."""
    managed = [dict(message) for message in messages]
    system_message = managed[:1] if managed and managed[0].get("role") == "system" else []
    first_removable_index = len(system_message)
    removed = 0

    while count_message_tokens(managed, encoding_name) > budget:
        if len(managed) <= first_removable_index:
            break
        managed.pop(first_removable_index)
        removed += 1

    result = HistoryManagementResult(
        messages=managed,
        input_tokens=count_message_tokens(managed, encoding_name),
        budget=budget,
        removed_messages=removed,
    )
    if not result.fits_budget:
        raise ValueError(
            "The current request is too large for the configured context budget."
        )
    return result


def manage_history(
    messages: List[Message],
    context_limit: int,
    reserved_output_tokens: int = 1000,
    safety_margin_tokens: int = 200,
    strategy: str = "trim",
    encoding_name: str = "cl100k_base",
    summarizer: Optional[Callable[[List[Message]], str]] = None,
) -> HistoryManagementResult:
    """Keep messages within the request budget using trimming or one summary.

    The first system message is always preserved. Summary mode requires a
    caller-provided summarizer and falls back to trimming if the summary still
    cannot fit.
    """
    if strategy not in {"trim", "summarize"}:
        raise ValueError("history strategy must be either 'trim' or 'summarize'.")

    budget = _history_budget(
        context_limit,
        reserved_output_tokens,
        safety_margin_tokens,
    )
    initial = [dict(message) for message in messages]
    if count_message_tokens(initial, encoding_name) <= budget:
        return HistoryManagementResult(
            messages=initial,
            input_tokens=count_message_tokens(initial, encoding_name),
            budget=budget,
        )

    if strategy == "summarize" and summarizer is not None:
        system_count = 1 if initial and initial[0].get("role") == "system" else 0
        if len(initial) > system_count + 1:
            removable = initial[system_count:-1]
            latest_message = initial[-1]
        else:
            removable = []
            latest_message = None
        if removable:
            summary = summarizer(removable).strip()
            if summary:
                summarized = (
                    initial[:system_count]
                    + [{"role": "system", "content": f"Conversation summary:\n{summary}"}]
                    + ([latest_message] if latest_message else [])
                )
                result = trim_messages(summarized, budget, encoding_name)
                if result.input_tokens <= budget:
                    return HistoryManagementResult(
                        messages=result.messages,
                        input_tokens=result.input_tokens,
                        budget=budget,
                        removed_messages=len(removable),
                        summarized_messages=len(removable),
                        summary_message=summarized[system_count],
                    )

    return trim_messages(initial, budget, encoding_name)
