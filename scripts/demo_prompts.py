#!/usr/bin/env python3
"""Executable demonstration script for ChronoLex prompt engineering experiments.

Demonstrates:
1. System vs. user role separation.
2. Vague vs. specific prompt comparison.
3. Explicit output constraints with safe JSON parsing.
4. ChronoLex regulatory grounding prompt with context delimiters and insufficient evidence handling.

Usage:
    python scripts/demo_prompts.py
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add apps/api to sys.path
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from dotenv import load_dotenv

# Load root .env file if available
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("demo_prompts")


def run_all_experiments() -> int:
    """Executes all prompt engineering experiments."""
    from app.core.config import settings
    from app.services.llm import (
        LLMAuthenticationError,
        LLMConfigurationError,
        LLMConnectionError,
        LLMProviderError,
        LLMRateLimitError,
    )
    from app.services.prompt_service import (
        build_grounded_messages,
        build_json_constraint_messages,
        build_system_user_messages,
        compare_vague_and_specific_prompts,
        parse_json_safely,
        run_grounded_query,
        run_json_constraint_experiment,
        run_system_user_experiment,
    )

    logger.info("Initializing ChronoLex Prompt Engineering Demonstration...")
    logger.info("Provider Base URL: %s", settings.OPENAI_BASE_URL)
    logger.info("Configured Chat Model: %s", settings.CHAT_MODEL)

    has_credentials = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())

    print("\n" + "=" * 70)
    print(" CHRONOLEX PROMPT ENGINEERING EXPERIMENTS ")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # Experiment 1: System vs User Role Separation
    # -----------------------------------------------------------------------
    print("\n[1] EXPERIMENT 1: System vs. User Role Separation")
    print("-" * 70)
    messages_1 = build_system_user_messages()
    print("System Message (Persona, Scope, Guardrails):")
    print(f"  > {messages_1[0]['content']}")
    print("User Message (Specific Query/Task):")
    print(f"  > {messages_1[1]['content']}")

    if has_credentials:
        try:
            exp1 = run_system_user_experiment()
            print(f"\nModel Answer: {exp1['answer']}")
            if exp1.get("usage"):
                print(f"Token Usage:  {exp1['usage']}")
        except Exception as e:
            logger.error("Experiment 1 failed: %s", e)
    else:
        print("\n[Live execution skipped: No OPENAI_API_KEY configured.]")

    # -----------------------------------------------------------------------
    # Experiment 2: Vague vs Specific Prompt Comparison
    # -----------------------------------------------------------------------
    print("\n[2] EXPERIMENT 2: Vague vs. Specific Prompt Comparison")
    print("-" * 70)
    print("System Instruction: 'You are concise and factual.'")
    print("Comparing two independent queries:")
    print("  Variant A (Vague):    'Explain our refund policy.'")
    print("  Variant B (Specific): 'In one sentence, state the refund window in days.'")

    if has_credentials:
        try:
            comparison = compare_vague_and_specific_prompts()
            for item in comparison:
                print(f"\n-> [{item.prompt_type.upper()}] Prompt: {item.prompt}")
                print(f"   Answer: {item.answer}")
                if item.usage:
                    print(f"   Tokens: Prompt={item.usage.prompt_tokens}, Completion={item.usage.completion_tokens}, Total={item.usage.total_tokens}")
        except Exception as e:
            logger.error("Experiment 2 failed: %s", e)
    else:
        print("\n[Live execution skipped: No OPENAI_API_KEY configured.]")

    # -----------------------------------------------------------------------
    # Experiment 3: Explicit Output Constraints (JSON)
    # -----------------------------------------------------------------------
    print("\n[3] EXPERIMENT 3: Explicit Output Constraints (Structured JSON)")
    print("-" * 70)
    messages_3 = build_json_constraint_messages()
    print(f"System Message:\n  > {messages_3[0]['content']}")
    print(f"User Message:\n  > {messages_3[1]['content']}")

    if has_credentials:
        try:
            exp3 = run_json_constraint_experiment()
            print(f"\nRaw Model Output:\n{exp3.raw_answer}")
            print(f"JSON Parsed Valid: {exp3.is_valid_json}")
            if exp3.parsed_json:
                print(f"Parsed Content:    {json.dumps(exp3.parsed_json, indent=2)}")
            if exp3.parsing_error:
                print(f"Parsing Error:     {exp3.parsing_error}")
        except Exception as e:
            logger.error("Experiment 3 failed: %s", e)
    else:
        print("\n[Live execution skipped: No OPENAI_API_KEY configured.]")

    # -----------------------------------------------------------------------
    # Experiment 4: ChronoLex Grounding Prompt & Insufficient Evidence
    # -----------------------------------------------------------------------
    print("\n[4] EXPERIMENT 4: ChronoLex Regulatory Grounding Prompt")
    print("-" * 70)
    sample_context = (
        "RBI Master Direction - KYC Direction, 2016 (Updated May 04, 2023).\n"
        "Section 38: Money Laundering records including accounts files and business correspondence "
        "shall be preserved for at least five years after the business relationship has ended."
    )
    question = "How long must banks preserve KYC and account records after account closure?"

    grounded_msgs = build_grounded_messages(question=question, context=sample_context)
    print(f"System Grounding Guardrail:\n{grounded_msgs[0]['content']}\n")
    print(f"User Message with Delimited Evidence Context:\n{grounded_msgs[1]['content']}")

    if has_credentials:
        try:
            print("\n-> Query With Valid Context:")
            res_valid = run_grounded_query(question=question, context=sample_context)
            print(f"Answer:               {res_valid.answer}")
            print(f"Evidence Sufficient:  {res_valid.evidence_sufficient}")

            print("\n-> Query With Empty/Insufficient Context:")
            res_empty = run_grounded_query(question="What is the capital adequacy requirement?", context="")
            print(f"Answer:               {res_empty.answer}")
            print(f"Evidence Sufficient:  {res_empty.evidence_sufficient}")
        except Exception as e:
            logger.error("Experiment 4 failed: %s", e)
    else:
        print("\n-> Insufficient Context Handling (Demonstration without API call):")
        res_empty = run_grounded_query(question="What is the capital adequacy requirement?", context="")
        print(f"Answer:               {res_empty.answer}")
        print(f"Evidence Sufficient:  {res_empty.evidence_sufficient}")

    print("\n" + "=" * 70)
    if not has_credentials:
        print("[Notice] Real API calls skipped because OPENAI_API_KEY is not set.")
        print("Set OPENAI_API_KEY in .env to run live model completions.")
    else:
        print("All experiments completed successfully.")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(run_all_experiments())
