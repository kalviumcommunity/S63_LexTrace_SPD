"""Automated tests for ChronoLex structured output, JSON parsing, validation, and error recovery.

All tests operate offline with mocked OpenAI client responses and require no paid API calls.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
)
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.main import app
from app.models.llm import TokenUsage
from app.models.structured import (
    StructuredAnswer,
    StructuredRequest,
    StructuredResponse,
)
from app.services.llm import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMProviderError,
    LLMService,
    llm_service,
)
from app.services.structured_service import (
    DEFAULT_STRUCTURED_SYSTEM_PROMPT,
    StructuredOutputError,
    request_structured_completion,
)
from app.utils.json_parsing import (
    parse_and_validate,
    parse_response,
    strip_code_fences,
    validate_schema,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def make_mock_completion(
    content: str,
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 25,
    completion_tokens: int = 15,
    total_tokens: int = 40,
) -> MagicMock:
    """Creates a mock response object mirroring openai ChatCompletion."""
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_resp.choices = [mock_choice]
    mock_resp.model = model

    if prompt_tokens is not None:
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = prompt_tokens
        mock_usage.completion_tokens = completion_tokens
        mock_usage.total_tokens = total_tokens
        mock_resp.usage = mock_usage
    else:
        mock_resp.usage = None

    return mock_resp


# ---------------------------------------------------------------------------
# 1. JSON Parser Unit Tests
# ---------------------------------------------------------------------------


def test_parse_response_valid_json():
    """Verifies that valid JSON containing required fields is parsed successfully."""
    raw = '{"answer": "30 days from transaction date", "source": "Circular 2023-B"}'
    data, err = parse_response(raw)

    assert err is None
    assert isinstance(data, dict)
    assert data["answer"] == "30 days from transaction date"
    assert data["source"] == "Circular 2023-B"


def test_parse_response_markdown_code_fences():
    """Verifies that JSON wrapped in markdown code fences is stripped and parsed safely."""
    raw = """```json
    {
        "answer": "Grounded answer",
        "source": "RBI/2021/14"
    }
    ```"""
    data, err = parse_response(raw)

    assert err is None
    assert isinstance(data, dict)
    assert data["answer"] == "Grounded answer"
    assert data["source"] == "RBI/2021/14"


def test_parse_response_malformed_json():
    """Verifies that malformed syntax returns a clear validation error without crashing."""
    raw = '{"answer": "Broken JSON without closing brace"'
    data, err = parse_response(raw)

    assert data is None
    assert err == "malformed JSON"


def test_parse_response_non_string_and_empty():
    """Verifies that empty string, None, or invalid types return malformed JSON."""
    assert parse_response("")[0] is None
    assert parse_response(None)[0] is None
    assert parse_response(12345)[0] is None


def test_parse_response_missing_fields():
    """Verifies that missing required fields are identified and reported."""
    # Missing 'source'
    raw_missing_source = '{"answer": "Only answer provided"}'
    data, err = parse_response(raw_missing_source)
    assert data is None
    assert "missing fields" in err
    assert "source" in err

    # Missing 'answer'
    raw_missing_answer = '{"source": "Only source provided"}'
    data, err = parse_response(raw_missing_answer)
    assert data is None
    assert "missing fields" in err
    assert "answer" in err

    # Missing both
    data, err = parse_response("{}")
    assert data is None
    assert "missing fields" in err
    assert "answer" in err and "source" in err


def test_parse_response_array_instead_of_object():
    """Verifies that a JSON array is rejected because a JSON object is expected."""
    raw = '[{"answer": "In array", "source": "Doc 1"}]'
    data, err = parse_response(raw)

    assert data is None
    assert err == "expected a JSON object"


def test_parse_response_primitives_instead_of_object():
    """Verifies that JSON primitives (string, number, boolean) are rejected."""
    for primitive in ['"Just a plain string"', "42", "true", "null"]:
        data, err = parse_response(primitive)
        assert data is None
        assert err == "expected a JSON object"


# ---------------------------------------------------------------------------
# 2. Pydantic Model Validation Unit Tests
# ---------------------------------------------------------------------------


def test_pydantic_valid_structured_answer():
    """Verifies that valid fields successfully instantiate StructuredAnswer."""
    model = StructuredAnswer(
        answer="The compliance window is 48 hours.",
        source="Basel III Accord Section 4",
    )
    assert model.answer == "The compliance window is 48 hours."
    assert model.source == "Basel III Accord Section 4"


def test_pydantic_incorrect_field_types():
    """Verifies that non-string field types (int, list, dict, bool) are strictly rejected."""
    with pytest.raises(ValidationError):
        StructuredAnswer.model_validate({"answer": 12345, "source": "Circular 1"})

    with pytest.raises(ValidationError):
        StructuredAnswer.model_validate({"answer": True, "source": "Circular 1"})

    with pytest.raises(ValidationError):
        StructuredAnswer.model_validate({"answer": "Answer", "source": ["Circular 1"]})


def test_pydantic_empty_or_whitespace_fields():
    """Verifies that empty strings and whitespace-only strings are rejected."""
    # Empty string
    with pytest.raises(ValidationError):
        StructuredAnswer(answer="", source="Circular 1")

    with pytest.raises(ValidationError):
        StructuredAnswer(answer="Valid answer", source="")

    # Whitespace-only string
    with pytest.raises(ValidationError):
        StructuredAnswer(answer="    ", source="Circular 1")

    with pytest.raises(ValidationError):
        StructuredAnswer(answer="Valid answer", source="   \n\t  ")


def test_reusable_schema_validator():
    """Verifies that the generic schema validation function supports custom Pydantic schemas."""
    class CustomPolicySchema(BaseModel):
        policy_id: str = Field(min_length=1)
        effective_year: int

    # Valid data
    res, err = validate_schema(
        {"policy_id": "POL-99", "effective_year": 2024},
        schema=CustomPolicySchema,
    )
    assert err is None
    assert res.policy_id == "POL-99"
    assert res.effective_year == 2024

    # Invalid data
    res, err = validate_schema(
        {"policy_id": "", "effective_year": "not-an-int"},
        schema=CustomPolicySchema,
    )
    assert res is None
    assert err is not None


# ---------------------------------------------------------------------------
# 3. Structured LLM Service & Bounded Recovery Tests
# ---------------------------------------------------------------------------


def test_structured_llm_successful_extraction():
    """Verifies successful LLM response extraction and parsing on first attempt."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_completion(
        content='{"answer": "The refund window is 14 days.", "source": "Policy Section 2.1"}',
        model="gpt-4o-mini",
        prompt_tokens=30,
        completion_tokens=20,
    )

    validated, chat_resp, retries = request_structured_completion(
        question="What is the refund window?",
        client=mock_client,
    )

    assert retries == 0
    assert validated.answer == "The refund window is 14 days."
    assert validated.source == "Policy Section 2.1"
    assert chat_resp.model == "gpt-4o-mini"
    assert chat_resp.usage.prompt_tokens == 30
    assert mock_client.chat.completions.create.call_count == 1


def test_structured_llm_json_mode_and_temperature_passed():
    """Verifies that temperature=0 and response_format are passed when JSON mode is enabled."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_completion(
        content='{"answer": "Standard answer", "source": "Directive 1"}',
    )

    request_structured_completion(
        question="State the rule",
        temperature=0.0,
        use_json_mode=True,
        client=mock_client,
    )

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["temperature"] == 0.0
    assert call_kwargs["response_format"] == {"type": "json_object"}


def test_structured_llm_single_retry_recovery_succeeds():
    """Verifies that when attempt 1 returns malformed JSON, a single retry is executed and succeeds."""
    mock_client = MagicMock()
    first_bad = make_mock_completion(content="I am unable to answer in JSON directly: {bad")
    second_good = make_mock_completion(
        content='{"answer": "Recovered valid answer", "source": "Directive 2"}'
    )
    mock_client.chat.completions.create.side_effect = [first_bad, second_good]

    validated, chat_resp, retries = request_structured_completion(
        question="What is the threshold?",
        client=mock_client,
    )

    assert retries == 1
    assert validated.answer == "Recovered valid answer"
    assert validated.source == "Directive 2"
    assert mock_client.chat.completions.create.call_count == 2

    # Verify that the second call contained a reminder message with the assistant's prior response
    second_call_messages = mock_client.chat.completions.create.call_args_list[1][1]["messages"]
    assert len(second_call_messages) == 4
    assert second_call_messages[2]["role"] == "assistant"
    assert second_call_messages[3]["role"] == "user"
    assert "failed validation" in second_call_messages[3]["content"]


def test_structured_llm_both_attempts_fail_returns_structured_error():
    """Verifies that when both attempts fail, StructuredOutputError is raised rather than invalid data."""
    mock_client = MagicMock()
    first_bad = make_mock_completion(content="malformed json 1")
    second_bad = make_mock_completion(content="still malformed 2")
    mock_client.chat.completions.create.side_effect = [first_bad, second_bad]

    with pytest.raises(StructuredOutputError) as exc_info:
        request_structured_completion(
            question="What is the threshold?",
            client=mock_client,
        )

    err = exc_info.value
    assert err.retries == 1
    assert "malformed JSON" in err.validation_error
    assert mock_client.chat.completions.create.call_count == 2


def test_structured_llm_missing_fields_triggers_retry():
    """Verifies that missing required fields trigger the single retry."""
    mock_client = MagicMock()
    first_missing_source = make_mock_completion(content='{"answer": "Missing source field"}')
    second_fixed = make_mock_completion(
        content='{"answer": "Fixed answer", "source": "Circular 9"}'
    )
    mock_client.chat.completions.create.side_effect = [first_missing_source, second_fixed]

    validated, _, retries = request_structured_completion(
        question="What is the policy?",
        client=mock_client,
    )

    assert retries == 1
    assert validated.answer == "Fixed answer"
    assert validated.source == "Circular 9"
    assert mock_client.chat.completions.create.call_count == 2


def test_structured_llm_auth_and_config_errors_do_not_retry():
    """Verifies that authentication and configuration errors fail immediately with no retry."""
    # 1. Authentication failure (HTTP 401)
    mock_client = MagicMock()
    mock_response = MagicMock(status_code=401, headers={})
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        "Invalid API Key", response=mock_response, body=None
    )

    with pytest.raises(LLMAuthenticationError):
        request_structured_completion(
            question="What is the rule?",
            client=mock_client,
        )

    assert mock_client.chat.completions.create.call_count == 1

    # 2. Configuration error (missing API key)
    with patch.object(settings, "OPENAI_API_KEY", None):
        with pytest.raises(LLMConfigurationError):
            request_structured_completion(
                question="What is the rule?",
                client=None,
                service=LLMService(client=None),
            )


def test_structured_llm_unsupported_json_mode_fallback():
    """Verifies that an unsupported response_format error falls back without response_format and succeeds."""
    mock_client = MagicMock()

    # Create an APIStatusError for unsupported parameter (400)
    mock_response = MagicMock(status_code=400, headers={})
    err_body = {"message": "response_format is not supported by this model"}
    unsupported_err = APIStatusError(
        message="response_format is not supported by this model",
        response=mock_response,
        body=err_body,
    )

    valid_resp = make_mock_completion(
        content='{"answer": "Answer without json mode", "source": "Circular A"}'
    )
    mock_client.chat.completions.create.side_effect = [unsupported_err, valid_resp]

    validated, chat_resp, retries = request_structured_completion(
        question="What is the rule?",
        client=mock_client,
        use_json_mode=True,
    )

    assert validated.answer == "Answer without json mode"
    assert validated.source == "Circular A"
    assert mock_client.chat.completions.create.call_count == 2

    # Second call should have fallen back without response_format
    second_call_kwargs = mock_client.chat.completions.create.call_args_list[1][1]
    assert "response_format" not in second_call_kwargs


def test_structured_llm_service_method_delegation():
    """Verifies that llm_service.send_structured_completion executes properly."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_completion(
        content='{"answer": "Delegated answer", "source": "Source 10"}'
    )

    svc = LLMService(client=mock_client)
    validated, resp, retries = svc.send_structured_completion(
        question="Check delegation",
    )

    assert retries == 0
    assert validated.answer == "Delegated answer"
    assert validated.source == "Source 10"


# ---------------------------------------------------------------------------
# 4. FastAPI Endpoint Integration Tests (/api/llm/structured)
# ---------------------------------------------------------------------------


def test_api_structured_endpoint_success():
    """Verifies that POST /api/llm/structured returns 200 with validated structured JSON."""
    with patch("app.api.llm.request_structured_completion") as mock_service:
        mock_answer = StructuredAnswer(
            answer="Customers have 30 days to request a refund.",
            source="Internal Policy Section 3",
        )
        mock_chat_resp = MagicMock(
            model="gpt-4o-mini",
            usage=TokenUsage(
                prompt_tokens=20, completion_tokens=10, total_tokens=30, estimated_cost=None
            ),
        )
        mock_service.return_value = (mock_answer, mock_chat_resp, 0)

        response = client.post(
            "/api/llm/structured",
            json={"question": "What is the refund window?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Customers have 30 days to request a refund."
        assert data["source"] == "Internal Policy Section 3"
        assert data["model"] == "gpt-4o-mini"
        assert data["retries"] == 0


def test_api_structured_endpoint_empty_question_validation():
    """Verifies that POST /api/llm/structured returns 422 for empty or whitespace question."""
    response = client.post(
        "/api/llm/structured",
        json={"question": "   "},
    )
    assert response.status_code == 422


def test_api_structured_endpoint_validation_failure_returns_422():
    """Verifies that POST /api/llm/structured returns 422 when structured validation fails."""
    with patch("app.api.llm.request_structured_completion") as mock_service:
        mock_service.side_effect = StructuredOutputError(
            message="Model output failed structured JSON validation after 1 retry: malformed JSON",
            raw_response="invalid raw output",
            validation_error="malformed JSON",
            retries=1,
            status_code=422,
        )

        response = client.post(
            "/api/llm/structured",
            json={"question": "What is the refund window?"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "Structured output validation failed"
        assert data["detail"]["retries"] == 1


def test_api_structured_endpoint_auth_failure_returns_401():
    """Verifies that authentication errors map cleanly to HTTP 401."""
    with patch("app.api.llm.request_structured_completion") as mock_service:
        mock_service.side_effect = LLMAuthenticationError("Authentication failed (401)")

        response = client.post(
            "/api/llm/structured",
            json={"question": "What is the refund window?"},
        )

        assert response.status_code == 401
        assert "401" in response.json()["detail"]
