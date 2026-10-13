"""Reusable JSON response parser and schema validation utilities for ChronoLex.

Provides safe extraction, syntax validation, JSON object enforcement,
required field verification, and generic Pydantic schema validation without eval().
"""

import json
import re
from typing import Any, Dict, Optional, Sequence, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def strip_code_fences(text: str) -> str:
    """Strips markdown code fences (e.g., ```json ... ```) if present."""
    cleaned = text.strip()
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.search(fence_pattern, cleaned, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return cleaned


def parse_response(
    raw: Any,
    required: Sequence[str] = ("answer", "source"),
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parses a raw LLM response string into a validated dictionary.

    Args:
        raw: The raw text string from the model completion.
        required: Sequence of required field keys.

    Returns:
        Tuple of (parsed_dict, None) on success, or (None, error_message) on failure.
    """
    if raw is None or not isinstance(raw, str):
        return None, "malformed JSON"

    cleaned = strip_code_fences(raw)
    if not cleaned:
        return None, "malformed JSON"

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None, "malformed JSON"

    if not isinstance(data, dict):
        return None, "expected a JSON object"

    missing = [key for key in required if key not in data]
    if missing:
        return None, f"missing fields: {missing}"

    return data, None


def validate_schema(
    data: Dict[str, Any],
    schema: Type[T],
) -> Tuple[Optional[T], Optional[str]]:
    """Validates a dictionary against a Pydantic schema model.

    Args:
        data: The dictionary to validate.
        schema: The Pydantic model class.

    Returns:
        Tuple of (model_instance, None) on success, or (None, error_message) on failure.
    """
    if not isinstance(data, dict):
        return None, "expected a dictionary for schema validation"
    try:
        instance = schema.model_validate(data)
        return instance, None
    except ValidationError as err:
        return None, f"schema validation error: {err}"


def parse_and_validate(
    raw: Any,
    schema: Type[T],
    required: Optional[Sequence[str]] = None,
) -> Tuple[Optional[T], Optional[str]]:
    """Combines JSON parsing and Pydantic schema validation into a single call.

    Args:
        raw: The raw text string from the model.
        schema: The Pydantic model class to validate against.
        required: Optional explicit list of required keys. Defaults to schema.model_fields.keys().

    Returns:
        Tuple of (validated_model, None) on success, or (None, error_message) on failure.
    """
    req_keys = (
        required if required is not None else tuple(schema.model_fields.keys())
    )
    data, parse_err = parse_response(raw, required=req_keys)
    if parse_err is not None or data is None:
        return None, parse_err

    return validate_schema(data, schema=schema)
