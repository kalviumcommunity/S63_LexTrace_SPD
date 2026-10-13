#!/usr/bin/env python3
"""ChronoLex Tokenization, Token Counting, and Cost Estimation Demonstration Script.

Demonstrates:
1. Counting tokens in example strings (e.g., 'refund', 'What is our refund window?').
2. Counting tokens in a supplied UTF-8 text file or reporting absence of data/policy.txt.
3. Estimating API cost from input and output token counts with clear price formatting.
4. Estimating context-window budgets with component breakdowns (system, user, context, history, reserved output).
5. Estimating corpus-scale token counts and hypothetical batch costs across 4,000 documents.

Usage:
    python scripts/token_cost_demo.py
    python scripts/token_cost_demo.py --help
    python scripts/token_cost_demo.py --input-tokens 1500 --output-tokens 300
    python scripts/token_cost_demo.py --file path/to/document.txt
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Add apps/api to sys.path so app modules can be imported
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

ROOT_DIR = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("token_cost_demo")

from app.utils.tokenization import (
    calculate_cost,
    count_tokens,
    count_tokens_batch,
    count_tokens_in_directory,
    count_tokens_in_file,
    estimate_context_budget,
    estimate_corpus_scale,
    inspect_policy_file,
)


def run_demo(
    file_path: Optional[str] = None,
    encoding_name: str = "cl100k_base",
    input_tokens: int = 1200,
    output_tokens: int = 350,
    input_price_per_1k: float = 0.0005,
    output_price_per_1k: float = 0.0015,
    context_limit: int = 8192,
    reserved_output: int = 1000,
    safety_margin: int = 250,
    docs_dir: Optional[str] = None,
    hypothetical_corpus_docs: int = 4000,
) -> int:
    """Executes the complete offline tokenization and cost estimation demonstration."""
    print("=" * 80)
    print("CHRONOLEX: TOKENIZATION, TOKEN COUNTING & COST ESTIMATION DEMO")
    print("=" * 80)
    print(f"Selected Tokenizer Encoding: {encoding_name}")
    print("Note: Token counting and arithmetic run completely OFFLINE without model calls.")
    print("-" * 80)

    # ---------------------------------------------------------
    # 1. Token Counting on Example Strings
    # ---------------------------------------------------------
    print("\n[PART 1: TOKEN COUNTING ON EXAMPLE STRINGS]")
    print("Important Concept: A token != a word or character. Punctuation, sub-word syllables,")
    print("and casing influence token counts. Counts also vary across different tokenizers.")

    examples = [
        "refund",
        "What is our refund window?",
        "ChronoLex compliance assistant identifies Article 15 breaches under FINRA Rule 2010.",
        "   Whitespace, indentation, and special symbols: #!$%^&*()_+{}[]:;\"'<>?,./",
    ]

    for text in examples:
        token_count = count_tokens(text, encoding_name=encoding_name)
        word_count = len(text.split())
        char_count = len(text)
        print(f"\n  Text:       \"{text}\"")
        print(f"  Tokens:     {token_count} (Encoding: {encoding_name})")
        print(f"  Words:      {word_count} | Characters: {char_count}")

    # ---------------------------------------------------------
    # 2. Text File Token Counting & data/policy.txt Inspection
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("[PART 2: FILE TOKEN COUNTING & POLICY FILE INSPECTION]")

    # Check data/policy.txt specifically
    policy_status = inspect_policy_file(ROOT_DIR, encoding_name=encoding_name)
    if policy_status["exists"]:
        print(f"  Found '{policy_status['path']}': {policy_status['token_count']} tokens.")
    else:
        print(f"  Policy file check: '{policy_status['path']}' does NOT exist.")
        print(f"  Status Note: {policy_status['message']}")
        print("  How to supply a text file:")
        print("    1. Create 'data/policy.txt' with your regulatory text, OR")
        print("    2. Pass '--file <path/to/file.txt>' to this script.")

    # If user provided a specific file path
    if file_path:
        custom_path = Path(file_path)
        print(f"\n  Inspecting user-supplied file: '{custom_path}'")
        try:
            tokens_in_custom = count_tokens_in_file(custom_path, encoding_name=encoding_name)
            print(f"  File: {custom_path} -> Token Count: {tokens_in_custom}")
        except FileNotFoundError:
            print(f"  Error: Supplied file '{custom_path}' was not found.")
        except Exception as exc:
            print(f"  Error reading '{custom_path}': {exc}")

    # ---------------------------------------------------------
    # 3. API Cost Estimation
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("[PART 3: API COST ESTIMATION]")
    print("Formula: cost = (input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate)")
    print("Disclaimer: Prices used ($0.0005/1k input, $0.0015/1k output) are illustrative defaults.")
    print("Model-specific provider rates must be explicitly configured.")

    cost_result = calculate_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_price_per_1k=input_price_per_1k,
        output_price_per_1k=output_price_per_1k,
    )

    print(f"\n  Usage Scenario:")
    print(f"    Input Tokens:        {cost_result.input_tokens:,}")
    print(f"    Output Tokens:       {cost_result.output_tokens:,}")
    print(f"    Total Tokens:        {cost_result.total_tokens:,}")
    print(f"    Input Rate / 1k:     ${cost_result.input_price_per_1k:.6f}")
    print(f"    Output Rate / 1k:    ${cost_result.output_price_per_1k:.6f}")
    print(f"  Cost Breakdown:")
    print(f"    Input Cost:          {cost_result.formatted_input_cost}")
    print(f"    Output Cost:         {cost_result.formatted_output_cost}")
    print(f"    Total Cost:          {cost_result.formatted_total_cost}")

    # Edge cases breakdown (input-only, output-only, zero)
    zero_cost = calculate_cost(0, 0, input_price_per_1k, output_price_per_1k)
    input_only_cost = calculate_cost(1000, 0, input_price_per_1k, output_price_per_1k)
    output_only_cost = calculate_cost(0, 1000, input_price_per_1k, output_price_per_1k)
    print(f"  Edge case (0 tokens):             {zero_cost.formatted_total_cost}")
    print(f"  Edge case (1,000 input only):     {input_only_cost.formatted_total_cost}")
    print(f"  Edge case (1,000 output only):    {output_only_cost.formatted_total_cost}")

    # ---------------------------------------------------------
    # 4. Context-Window Budgeting
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("[PART 4: CONTEXT-WINDOW BUDGETING]")
    print("Accounting for System Prompt, User Query, Retrieved Context, Conversation History,")
    print("Reserved Output Tokens, and Safety Margin.")
    print("Note: Local text token counts are estimates; actual provider prompt processing")
    print("includes chat formatting tokens (<|im_start|>, roles, etc.).")

    # Sample components
    sample_system = (
        "You are ChronoLex, an AI regulatory compliance assistant. Analyze policy texts and "
        "cite official regulatory guidelines accurately."
    )
    sample_user = "What are the disclosure requirements for third-party loan servicing under Dodd-Frank?"
    sample_context = (
        "[Document 1 - CFPB Bulletin 2012-03]\n"
        "Financial institutions must oversee service providers to ensure compliance with Federal "
        "consumer financial laws.\n\n"
        "[Document 2 - Dodd-Frank Title X]\n"
        "Lenders are required to provide complete disclosure of loan modification options within 30 days."
    )
    sample_history = [
        "User: Hello ChronoLex.",
        "Assistant: Hello! I am ready to assist with regulatory compliance inquiries.",
    ]

    budget_result = estimate_context_budget(
        system_prompt=sample_system,
        user_question=sample_user,
        retrieved_context=sample_context,
        conversation_history=[{"role": "user", "content": h} for h in sample_history],
        context_limit=context_limit,
        reserved_output_tokens=reserved_output,
        safety_margin_tokens=safety_margin,
        encoding_name=encoding_name,
    )

    print(f"\n  Configured Context Limit:    {budget_result.context_limit:,} tokens")
    print(f"  Component Token Breakdown:")
    print(f"    - System Prompt:           {budget_result.breakdown.system_tokens:,} tokens")
    print(f"    - User Question:           {budget_result.breakdown.question_tokens:,} tokens")
    print(f"    - Retrieved Context:       {budget_result.breakdown.context_tokens:,} tokens")
    print(f"    - Conversation History:    {budget_result.breakdown.history_tokens:,} tokens")
    print(f"  Total Estimated Input:       {budget_result.breakdown.total_input_tokens:,} tokens")
    print(f"  Reserved Output:             {budget_result.breakdown.reserved_output_tokens:,} tokens")
    print(f"  Safety Margin:               {budget_result.breakdown.safety_margin_tokens:,} tokens")
    print(f"  Total Committed Tokens:      {budget_result.breakdown.total_demanded_tokens:,} tokens")
    print(f"  Remaining Capacity:          {budget_result.remaining_capacity:,} tokens")
    print(f"  Fits Within Budget?          {'YES (PASSED)' if budget_result.fits_budget else 'NO (OVER BUDGET)'}")
    print(f"  Status:                      {budget_result.status_message}")

    # Demonstrate an over-budget scenario
    tight_budget = estimate_context_budget(
        system_prompt=sample_system,
        user_question=sample_user,
        retrieved_context=sample_context,
        conversation_history=[{"role": "user", "content": h} for h in sample_history],
        context_limit=500,  # Deliberately restricted
        reserved_output_tokens=300,
        safety_margin_tokens=100,
        encoding_name=encoding_name,
    )
    overage = tight_budget.breakdown.total_demanded_tokens - tight_budget.context_limit
    print(f"\n  Over-budget Test Case (Limit: 500 tokens):")
    print(f"    Total Committed:           {tight_budget.breakdown.total_demanded_tokens:,} tokens")
    print(f"    Remaining Capacity:        {tight_budget.remaining_capacity:,} tokens")
    print(f"    Fits Within Budget?        {tight_budget.fits_budget} (Overage: {overage:,} tokens)")
    print(f"    Status Message:            {tight_budget.status_message}")
    print("    Handling Strategy: Report overage clearly so retrieval pipeline can reduce chunk count.")

    # ---------------------------------------------------------
    # 5. Corpus-Scale Estimation (e.g. 4,000 Documents)
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("[PART 5: CORPUS-SCALE TOKEN & COST ESTIMATION]")
    print("Key Architecture Distinctions:")
    print("  1. Local Tokenization: Fast, offline parsing via tiktoken. Zero API cost.")
    print("  2. Embedding Ingestion: One-time cost to convert docs into dense vectors for indexing.")
    print("  3. Chat Completion: Recurring cost per query to send relevant retrieved chunks into context.")

    if docs_dir and Path(docs_dir).is_dir():
        print(f"\n  Analyzing actual directory: '{docs_dir}'")
        actual_docs = count_tokens_in_directory(Path(docs_dir), encoding_name=encoding_name)
        if actual_docs:
            doc_counts = [tokens for _, tokens in actual_docs]
            stats = estimate_corpus_scale(doc_counts, target_document_count=len(doc_counts))
            print(f"    Found {stats.document_count} documents.")
            print(f"    Total Corpus Tokens:   {stats.total_tokens:,}")
            print(f"    Average / Min / Max:   {stats.avg_tokens_per_doc:.1f} / {stats.min_tokens_per_doc} / {stats.max_tokens_per_doc}")
        else:
            print("    No .txt files found in provided directory.")

    print(f"\nHypothetical Corpus Scale Example ({hypothetical_corpus_docs:,} Documents):")
    print("  (Assuming an illustrative average of ~750 tokens per regulatory document snippet)")
    hypothetical_counts = [600, 750, 900, 750]  # Representative sample
    corpus_stats = estimate_corpus_scale(
        document_token_counts=hypothetical_counts,
        target_document_count=hypothetical_corpus_docs,
        input_price_per_1k=input_price_per_1k,
    )
    print(f"    Sample Document Count:     {corpus_stats.document_count}")
    print(f"    Sample Average Tokens:     {corpus_stats.avg_tokens_per_doc:.1f}")
    print(f"    Target Scaled Documents:   {corpus_stats.target_scale_documents:,}")
    print(f"    Estimated Total Tokens:    {corpus_stats.projected_corpus_tokens:,}")
    print(f"    Est. Chat Input Cost:      {corpus_stats.formatted_estimated_cost} (@ ${input_price_per_1k}/1k tokens)")
    print("  Note: In a RAG architecture, all 4,000 documents are NOT sent into chat context simultaneously;")
    print("  instead, top-k chunks (e.g. 3-5 snippets ~1,500 tokens) are retrieved per query.")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("=" * 80)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ChronoLex Tokenization, Token Counting, and Cost Estimation Demo."
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Optional path to a UTF-8 text file to count tokens for.",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="cl100k_base",
        help="tiktoken encoding name (default: cl100k_base).",
    )
    parser.add_argument(
        "--input-tokens",
        type=int,
        default=1200,
        help="Estimated input token count for cost demo (default: 1200).",
    )
    parser.add_argument(
        "--output-tokens",
        type=int,
        default=350,
        help="Estimated output token count for cost demo (default: 350).",
    )
    parser.add_argument(
        "--input-price",
        type=float,
        default=0.0005,
        help="Input price per 1,000 tokens (illustrative default: 0.0005).",
    )
    parser.add_argument(
        "--output-price",
        type=float,
        default=0.0015,
        help="Output price per 1,000 tokens (illustrative default: 0.0015).",
    )
    parser.add_argument(
        "--context-limit",
        type=int,
        default=8192,
        help="Context window limit in tokens (default: 8192).",
    )
    parser.add_argument(
        "--reserved-output",
        type=int,
        default=1000,
        help="Reserved tokens for LLM generation (default: 1000).",
    )
    parser.add_argument(
        "--safety-margin",
        type=int,
        default=250,
        help="Safety margin buffer tokens (default: 250).",
    )
    parser.add_argument(
        "--docs-dir",
        type=str,
        default=None,
        help="Optional directory containing .txt documents to inspect.",
    )
    parser.add_argument(
        "--corpus-scale",
        type=int,
        default=4000,
        help="Number of documents for corpus scale estimation (default: 4000).",
    )

    args = parser.parse_args()

    return run_demo(
        file_path=args.file,
        encoding_name=args.encoding,
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
        input_price_per_1k=args.input_price,
        output_price_per_1k=args.output_price,
        context_limit=args.context_limit,
        reserved_output=args.reserved_output,
        safety_margin=args.safety_margin,
        docs_dir=args.docs_dir,
        hypothetical_corpus_docs=args.corpus_scale,
    )


if __name__ == "__main__":
    sys.exit(main())
