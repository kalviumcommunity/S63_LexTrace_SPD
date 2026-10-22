"""Offline demonstration of bounded multi-turn conversation history."""

from __future__ import annotations

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.services.context_window import count_message_tokens, manage_history


CONTEXT_LIMIT = 120
RESERVED_OUTPUT = 20
SAFETY_MARGIN = 10


def summarize(old_messages: list[dict[str, str]]) -> str:
    """Deterministic stand-in for a summary model call."""
    topics = [message["content"].split(" about ", 1)[-1].rstrip(".") for message in old_messages if message["role"] == "user"]
    return f"Earlier turns covered: {', '.join(topics)}."


def run(strategy: str) -> None:
    history = [{"role": "system", "content": "You are a concise compliance assistant."}]
    budget = CONTEXT_LIMIT - RESERVED_OUTPUT - SAFETY_MARGIN

    print(f"\nStrategy: {strategy}")
    print(f"Context limit: {CONTEXT_LIMIT}; input budget: {budget}")
    print("turn | naive tokens | managed tokens | removed | summarized | status")

    for turn in range(1, 9):
        history.append(
            {
                "role": "user",
                "content": (
                    f"Turn {turn}: explain the regulatory requirement about "
                    "cross-border payment screening and its audit evidence."
                ),
            }
        )
        naive_tokens = count_message_tokens(history)
        result = manage_history(
            history,
            context_limit=CONTEXT_LIMIT,
            reserved_output_tokens=RESERVED_OUTPUT,
            safety_margin_tokens=SAFETY_MARGIN,
            strategy=strategy,
            summarizer=summarize if strategy == "summarize" else None,
        )
        history = result.messages + [
            {
                "role": "assistant",
                "content": (
                    "The requirement depends on the applicable rule version; "
                    "retain the source paragraph for audit review."
                ),
            }
        ]
        print(
            f"{turn:4} | {naive_tokens:12} | {result.input_tokens:14} | "
            f"{result.removed_messages:7} | {result.summarized_messages:10} | "
            f"{'within budget' if result.fits_budget else 'OVERFLOW'}"
        )


if __name__ == "__main__":
    print("Naive history grows beyond the input budget; managed requests remain bounded.")
    run("trim")
    run("summarize")
