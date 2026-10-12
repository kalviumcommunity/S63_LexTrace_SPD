#!/usr/bin/env python3
"""Executable demonstration script for OpenAI-compatible LLM API access.

This script demonstrates:
1. Loading environment configuration via python-dotenv.
2. Initializing the OpenAI-compatible client.
3. Sending a sample chat completion request with system & user messages.
4. Logging request, response, and token usage using Python's logging module.
5. Gracefully handling common API errors (HTTP 401, 429, connection errors).

Usage:
    python scripts/demo_llm.py
"""

import logging
import os
import sys
from pathlib import Path

# Add apps/api to sys.path so app modules can be imported directly
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
logger = logging.getLogger("demo_llm")


def run_demonstration() -> int:
    """Executes the demonstration chat completion flow."""
    from app.core.config import settings
    from app.services.llm import (
        LLMAuthenticationError,
        LLMConfigurationError,
        LLMConnectionError,
        LLMProviderError,
        LLMRateLimitError,
        llm_service,
    )

    logger.info("Initializing ChronoLex LLM API demonstration...")
    logger.info("Provider Base URL: %s", settings.OPENAI_BASE_URL)
    logger.info("Configured Chat Model: %s", settings.CHAT_MODEL)

    # Check for credentials before calling provider
    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.strip():
        logger.warning(
            "OPENAI_API_KEY is not configured. "
            "Please create a .env file based on .env.example with your provider credentials to run live completions."
        )
        print("\n[Notice] No OPENAI_API_KEY found in environment or .env file.")
        print("To test against a live provider, set OPENAI_API_KEY in .env and run again.\n")
        return 0

    user_message = "Say hello in one sentence."
    system_prompt = "You are a concise assistant."

    print("\n--- Sending Chat Completion Request ---")
    print(f"System: {system_prompt}")
    print(f"User:   {user_message}\n")

    try:
        response = llm_service.send_chat_completion(
            user_message=user_message,
            system_prompt=system_prompt,
        )

        print("--- Response Received ---")
        print(f"Model:  {response.model}")
        print(f"Answer: {response.answer}")
        if response.usage:
            print(
                f"Usage:  Prompt={response.usage.prompt_tokens}, "
                f"Completion={response.usage.completion_tokens}, "
                f"Total={response.usage.total_tokens}"
            )
        print("-------------------------\n")
        return 0

    except LLMAuthenticationError as e:
        logger.error("%s", e.message)
        print(f"\n[Error] {e.message}\n")
        return 1

    except LLMRateLimitError as e:
        logger.error("%s", e.message)
        print(f"\n[Error] {e.message}\n")
        return 1

    except LLMConnectionError as e:
        logger.error("%s", e.message)
        print(f"\n[Error] {e.message}\n")
        return 1

    except (LLMConfigurationError, LLMProviderError) as e:
        logger.error("%s", e.message)
        print(f"\n[Error] {e.message}\n")
        return 1

    except Exception as e:
        logger.exception("Unexpected error during demonstration: %s", e)
        print(f"\n[Error] Unexpected error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_demonstration())
