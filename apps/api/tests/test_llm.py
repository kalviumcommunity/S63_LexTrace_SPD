"""Unit and integration tests for ChronoLex LLM API integration.

Tests use mocks so no live external API calls or credentials are required.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from app.core.config import settings
from app.main import app
from app.models.llm import ChatRequest, ChatResponse, TokenUsage
from app.services.llm import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMService,
    get_llm_client,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers for constructing mock OpenAI completion responses
# ---------------------------------------------------------------------------


def create_mock_completion_response(
    content="Hello! It is nice to meet you.",
    model="gpt-4o-mini",
    prompt_tokens=15,
    completion_tokens=8,
    total_tokens=23,
):
    """Creates a mock response object mirroring openai.types.chat.ChatCompletion."""
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
# Unit Tests: LLM Service
# ---------------------------------------------------------------------------


def test_successful_chat_completion_and_extraction():
    """Test 1 & 2: Successful completion and correct message content extraction."""
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = create_mock_completion_response(
        content="Greetings from ChronoLex.",
        model="gpt-4o-mini",
    )

    service = LLMService(client=mock_openai)
    result = service.send_chat_completion(
        user_message="Say hello in one sentence.",
        system_prompt="You are a concise assistant.",
    )

    assert isinstance(result, ChatResponse)
    assert result.answer == "Greetings from ChronoLex."
    assert result.model == "gpt-4o-mini"
    mock_openai.chat.completions.create.assert_called_once()
    call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Say hello in one sentence."},
    ]


def test_token_usage_extraction():
    """Test 3: Token usage metadata extraction."""
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = create_mock_completion_response(
        prompt_tokens=42,
        completion_tokens=18,
        total_tokens=60,
    )

    service = LLMService(client=mock_openai)
    result = service.send_chat_completion(user_message="Summarize circular 402.")

    assert result.usage is not None
    assert result.usage.prompt_tokens == 42
    assert result.usage.completion_tokens == 18
    assert result.usage.total_tokens == 60


def test_safe_handling_of_empty_or_none_response():
    """Safely handles missing choices or none content without crashing."""
    mock_openai = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = []
    mock_resp.usage = None
    mock_resp.model = "gpt-4o-mini"
    mock_openai.chat.completions.create.return_value = mock_resp

    service = LLMService(client=mock_openai)
    result = service.send_chat_completion(user_message="Test empty")

    assert result.answer == ""
    assert result.usage is None


def test_missing_environment_configuration():
    """Test 4: Missing OPENAI_API_KEY raises LLMConfigurationError."""
    with patch.object(settings, "OPENAI_API_KEY", None):
        with pytest.raises(LLMConfigurationError) as exc_info:
            get_llm_client()
        assert "OPENAI_API_KEY is not configured" in str(exc_info.value)


def test_authentication_error_handling():
    """Test 5: AuthenticationError (HTTP 401) handling and sanitized message."""
    mock_openai = MagicMock()
    mock_response = MagicMock(status_code=401, headers={})
    mock_openai.chat.completions.create.side_effect = AuthenticationError(
        message="Incorrect API key provided: sk-secret-12345",
        response=mock_response,
        body={"error": {"message": "Invalid API key"}},
    )

    service = LLMService(client=mock_openai)
    with pytest.raises(LLMAuthenticationError) as exc_info:
        service.send_chat_completion(user_message="Hello")

    assert "Authentication failed (401)" in str(exc_info.value)
    # Ensure sensitive credentials are never leaked in the error message
    assert "sk-secret-12345" not in str(exc_info.value)


def test_rate_limit_error_handling():
    """Test 6: RateLimitError (HTTP 429) handling."""
    mock_openai = MagicMock()
    mock_response = MagicMock(status_code=429, headers={})
    mock_openai.chat.completions.create.side_effect = RateLimitError(
        message="Rate limit reached for requests",
        response=mock_response,
        body={"error": {"message": "You exceeded your current quota"}},
    )

    # Use max_retries=0 for fast test execution
    service = LLMService(client=mock_openai, max_retries=0)
    with pytest.raises(LLMRateLimitError) as exc_info:
        service.send_chat_completion(user_message="Hello")

    assert "Rate limited (429)" in str(exc_info.value)


def test_connection_failure_handling():
    """Test 7: Connection failure and timeout handling."""
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.side_effect = APIConnectionError(
        request=MagicMock()
    )

    service = LLMService(client=mock_openai, max_retries=0)
    with pytest.raises(LLMConnectionError) as exc_info:
        service.send_chat_completion(user_message="Hello")

    assert "Connection error" in str(exc_info.value)


def test_empty_user_message_validation():
    """Test 8: Empty user message validation in service and Pydantic model."""
    service = LLMService()

    with pytest.raises(ValueError):
        service.send_chat_completion("")

    with pytest.raises(ValueError):
        service.send_chat_completion("   \n\t  ")

    with pytest.raises(ValueError):
        ChatRequest(message="")

    with pytest.raises(ValueError):
        ChatRequest(message="   ")


# ---------------------------------------------------------------------------
# Integration Tests: FastAPI Endpoints (/api/llm/chat)
# ---------------------------------------------------------------------------


def test_fastapi_chat_endpoint_success():
    """Test 9: Successful response from POST /api/llm/chat."""
    mock_resp = ChatResponse(
        answer="Hello! It is nice to meet you.",
        model="gpt-4o-mini",
        usage=TokenUsage(prompt_tokens=15, completion_tokens=8, total_tokens=23),
    )

    with patch("app.api.llm.llm_service.send_chat_completion", return_value=mock_resp):
        response = client.post(
            "/api/llm/chat",
            json={"message": "Say hello in one sentence."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Hello! It is nice to meet you."
    assert data["model"] == "gpt-4o-mini"
    assert data["usage"] == {
        "prompt_tokens": 15,
        "completion_tokens": 8,
        "total_tokens": 23,
    }


def test_fastapi_chat_endpoint_empty_message_rejected():
    """Test empty message validation returns HTTP 422 Unprocessable Entity."""
    response = client.post(
        "/api/llm/chat",
        json={"message": ""},
    )
    assert response.status_code == 422


def test_fastapi_chat_endpoint_whitespace_message_rejected():
    """Test whitespace-only message returns HTTP 422."""
    response = client.post(
        "/api/llm/chat",
        json={"message": "    "},
    )
    assert response.status_code == 422


def test_fastapi_chat_endpoint_auth_error_status_401():
    """Test 10: Provider HTTP 401 maps to HTTP 401 with clear message."""
    with patch(
        "app.api.llm.llm_service.send_chat_completion",
        side_effect=LLMAuthenticationError(),
    ):
        response = client.post(
            "/api/llm/chat",
            json={"message": "Hello"},
        )

    assert response.status_code == 401
    assert "Authentication failed (401)" in response.json()["detail"]


def test_fastapi_chat_endpoint_rate_limit_status_429():
    """Test 10: Provider HTTP 429 maps to HTTP 429 with clear message."""
    with patch(
        "app.api.llm.llm_service.send_chat_completion",
        side_effect=LLMRateLimitError(),
    ):
        response = client.post(
            "/api/llm/chat",
            json={"message": "Hello"},
        )

    assert response.status_code == 429
    assert "Rate limited (429)" in response.json()["detail"]


def test_fastapi_chat_endpoint_connection_error_status_502():
    """Test 10: Provider connection error maps to HTTP 502 Bad Gateway."""
    with patch(
        "app.api.llm.llm_service.send_chat_completion",
        side_effect=LLMConnectionError(),
    ):
        response = client.post(
            "/api/llm/chat",
            json={"message": "Hello"},
        )

    assert response.status_code == 502
    assert "Connection error" in response.json()["detail"]


def test_fastapi_chat_endpoint_config_error_status_500():
    """Test 10: Missing configuration maps to HTTP 500 Internal Server Error."""
    with patch(
        "app.api.llm.llm_service.send_chat_completion",
        side_effect=LLMConfigurationError(),
    ):
        response = client.post(
            "/api/llm/chat",
            json={"message": "Hello"},
        )

    assert response.status_code == 500
    assert "Configuration error" in response.json()["detail"]
