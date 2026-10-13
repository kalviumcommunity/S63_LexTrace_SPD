"""Comprehensive unit and integration tests for ChronoLex tokenization, cost estimation, and context budgeting.

Verifies:
- Token counting for empty, short, and non-empty text strings.
- Consistency of repeated calls with same encoding.
- File reading, missing file handling, and empty file handling.
- Cost estimation for zero, input-only, output-only, and mixed token usage.
- Rejection of negative token counts or negative prices.
- Context budget calculations (within budget vs exceeded budget).
- Corpus scale statistics for empty, single, and multiple document lists.
- Enrichment of LLM response usage with cost calculations and missing usage resilience.
- API validation for POST /api/llm/token-estimate.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.llm import TokenUsage
from app.models.tokens import (
    ContextBudgetRequest,
    CostEstimateRequest,
    TokenCountRequest,
)
from app.services.llm import LLMService
from app.utils.tokenization import (
    calculate_cost,
    count_tokens,
    count_tokens_batch,
    count_tokens_in_directory,
    count_tokens_in_file,
    estimate_context_budget,
    estimate_corpus_scale,
    get_tokenizer,
    inspect_policy_file,
)


@pytest.fixture
def client():
    return TestClient(app)


# ===========================================================================
# 1. Token Counting Unit Tests
# ===========================================================================


class TestTokenCounting:
    """Tests for tiktoken-based string and file token counting."""

    def test_count_empty_string(self):
        """Empty string must return exactly 0 tokens."""
        assert count_tokens("") == 0
        assert count_tokens("   ") > 0  # Whitespace alone is encoded into tokens

    def test_count_known_examples(self):
        """Tokens differ from words: verify non-zero counts for sample phrases."""
        count_single = count_tokens("refund")
        assert count_single == 1

        count_question = count_tokens("What is our refund window?")
        assert count_question == 6
        assert count_question > count_single

    def test_consistent_repeated_calls(self):
        """Repeated tokenization of identical input produces idempotent counts."""
        text = "ChronoLex regulatory compliance verification engine."
        first = count_tokens(text, encoding_name="cl100k_base")
        second = count_tokens(text, encoding_name="cl100k_base")
        third = count_tokens(text, encoding_name="cl100k_base")
        assert first == second == third
        assert first > 0

    def test_batch_counting(self):
        """Batch counting returns a list of integer token counts matching inputs."""
        inputs = ["refund", "What is our refund window?", ""]
        counts = count_tokens_batch(inputs)
        assert len(counts) == 3
        assert counts[0] == 1
        assert counts[1] == 6
        assert counts[2] == 0

    def test_invalid_encoding_name_raises(self):
        """Specifying an unknown encoding name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or unsupported tokenizer encoding"):
            count_tokens("test", encoding_name="nonexistent_encoding_xyz")

    def test_count_in_file(self, tmp_path: Path):
        """Successfully counts tokens in a UTF-8 text file."""
        sample_file = tmp_path / "test_doc.txt"
        sample_file.write_text("Dodd-Frank Act section 1021 compliance requirements.", encoding="utf-8")
        tokens = count_tokens_in_file(sample_file)
        assert tokens > 0

    def test_count_in_empty_file(self, tmp_path: Path):
        """Empty file produces 0 tokens."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        assert count_tokens_in_file(empty_file) == 0

    def test_count_in_missing_file_raises(self, tmp_path: Path):
        """Missing file raises FileNotFoundError."""
        missing = tmp_path / "does_not_exist.txt"
        with pytest.raises(FileNotFoundError):
            count_tokens_in_file(missing)

    def test_inspect_policy_file_when_missing(self, tmp_path: Path):
        """Missing data/policy.txt returns clean dict without crashing or raising."""
        res = inspect_policy_file(repo_root=tmp_path)
        assert res["exists"] is False
        assert res["token_count"] == 0
        assert "not found" in res["message"].lower()

    def test_inspect_policy_file_when_present(self, tmp_path: Path):
        """Existing data/policy.txt returns exists=True and integer token_count."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        policy = data_dir / "policy.txt"
        policy.write_text("Standard 30-day refund window policy text.", encoding="utf-8")

        res = inspect_policy_file(repo_root=tmp_path)
        assert res["exists"] is True
        assert res["token_count"] is not None
        assert res["token_count"] > 0


# ===========================================================================
# 2. Cost Estimation Unit Tests
# ===========================================================================


class TestCostEstimation:
    """Tests for API cost estimation formula and validations."""

    def test_zero_tokens(self):
        """Zero tokens must evaluate to zero cost."""
        res = calculate_cost(input_tokens=0, output_tokens=0, input_price_per_1k=0.0005, output_price_per_1k=0.0015)
        assert res.input_cost == 0.0
        assert res.output_cost == 0.0
        assert res.total_cost == 0.0
        assert res.formatted_total_cost == "$0.000000"

    def test_input_only_usage(self):
        """Input-only tokens compute cost without output contribution."""
        res = calculate_cost(input_tokens=2000, output_tokens=0, input_price_per_1k=0.0005, output_price_per_1k=0.0015)
        # 2000 / 1000 * 0.0005 = 0.001
        assert pytest.approx(res.input_cost, rel=1e-5) == 0.001
        assert res.output_cost == 0.0
        assert pytest.approx(res.total_cost, rel=1e-5) == 0.001

    def test_output_only_usage(self):
        """Output-only tokens compute cost without input contribution."""
        res = calculate_cost(input_tokens=0, output_tokens=1000, input_price_per_1k=0.0005, output_price_per_1k=0.0015)
        # 1000 / 1000 * 0.0015 = 0.0015
        assert res.input_cost == 0.0
        assert pytest.approx(res.output_cost, rel=1e-5) == 0.0015
        assert pytest.approx(res.total_cost, rel=1e-5) == 0.0015

    def test_mixed_usage(self):
        """Mixed input and output tokens compute combined cost accurately."""
        res = calculate_cost(input_tokens=1000, output_tokens=500, input_price_per_1k=0.0005, output_price_per_1k=0.0015)
        # Input: 1000 / 1000 * 0.0005 = 0.0005
        # Output: 500 / 1000 * 0.0015 = 0.00075
        # Total: 0.00125
        assert pytest.approx(res.input_cost, rel=1e-5) == 0.0005
        assert pytest.approx(res.output_cost, rel=1e-5) == 0.00075
        assert pytest.approx(res.total_cost, rel=1e-5) == 0.00125
        assert res.formatted_total_cost == "$0.001250"

    def test_rejection_of_negative_tokens(self):
        """Negative token counts must raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cost(input_tokens=-10, output_tokens=100)
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cost(input_tokens=100, output_tokens=-5)

    def test_rejection_of_negative_rates(self):
        """Negative price rates must raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cost(input_tokens=100, output_tokens=100, input_price_per_1k=-0.001)
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cost(input_tokens=100, output_tokens=100, output_price_per_1k=-0.001)


# ===========================================================================
# 3. Context-Window Budgeting Unit Tests
# ===========================================================================


class TestContextBudgeting:
    """Tests for prompt context window budget estimation."""

    def test_request_fits_within_budget(self):
        """A small prompt well under the limit reports fits_budget=True with positive remaining capacity."""
        res = estimate_context_budget(
            system_prompt="You are a compliance assistant.",
            user_question="What is the refund policy?",
            retrieved_context="Standard 30-day refund window.",
            context_limit=4096,
            reserved_output_tokens=500,
            safety_margin_tokens=100,
        )
        assert res.fits_budget is True
        assert res.remaining_capacity > 0
        assert res.context_limit == 4096
        assert res.breakdown.reserved_output_tokens == 500
        assert res.breakdown.safety_margin_tokens == 100
        assert res.breakdown.system_tokens > 0
        assert res.breakdown.question_tokens > 0
        assert res.breakdown.context_tokens > 0

    def test_request_exceeds_budget(self):
        """When total demanded tokens exceed context limit, fits_budget=False with negative capacity."""
        res = estimate_context_budget(
            system_prompt="You are a compliance assistant.",
            user_question="What is the refund policy?",
            retrieved_context="Standard 30-day refund window.",
            context_limit=100,  # Very small budget
            reserved_output_tokens=80,
            safety_margin_tokens=50,
        )
        assert res.fits_budget is False
        assert res.remaining_capacity < 0
        assert "exceeds context budget" in res.status_message

    def test_budget_with_conversation_history(self):
        """Conversation history tokens are properly aggregated in breakdown."""
        history = [
            {"role": "user", "content": "Hello."},
            {"role": "assistant", "content": "How can I help you today?"},
        ]
        res = estimate_context_budget(
            system_prompt="System instructions.",
            user_question="New question.",
            retrieved_context="",
            conversation_history=history,
            context_limit=2048,
        )
        assert res.breakdown.history_tokens > 0
        assert res.breakdown.total_input_tokens > res.breakdown.question_tokens

    def test_invalid_context_limit_raises(self):
        """Non-positive context limit raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            estimate_context_budget(context_limit=0)


# ===========================================================================
# 4. Corpus-Scale Statistics Unit Tests
# ===========================================================================


class TestCorpusScaleEstimation:
    """Tests for corpus token counting, averaging, and 4,000 document scaling."""

    def test_empty_document_counts(self):
        """Empty list of document token counts returns zeroed statistics safely."""
        res = estimate_corpus_scale([])
        assert res.document_count == 0
        assert res.total_tokens == 0
        assert res.avg_tokens_per_doc == 0.0
        assert res.projected_corpus_tokens == 0
        assert res.estimated_chat_input_cost == 0.0

    def test_single_document_count(self):
        """Single document statistics have matching avg, min, max."""
        res = estimate_corpus_scale([500], target_document_count=4000)
        assert res.document_count == 1
        assert res.total_tokens == 500
        assert res.avg_tokens_per_doc == 500.0
        assert res.min_tokens_per_doc == 500
        assert res.max_tokens_per_doc == 500
        # 4,000 * 500 = 2,000,000 tokens
        assert res.projected_corpus_tokens == 2_000_000

    def test_multiple_document_counts_and_extrapolation(self):
        """Calculates accurate min, max, avg, and extrapolates to target_document_count."""
        doc_counts = [500, 1000, 1500]
        res = estimate_corpus_scale(
            document_token_counts=doc_counts,
            target_document_count=4000,
            input_price_per_1k=0.0005,
        )
        assert res.document_count == 3
        assert res.total_tokens == 3000
        assert res.avg_tokens_per_doc == 1000.0
        assert res.min_tokens_per_doc == 500
        assert res.max_tokens_per_doc == 1500
        # 4000 * 1000 = 4,000,000 tokens
        assert res.projected_corpus_tokens == 4_000_000
        # Cost: 4,000,000 / 1000 * 0.0005 = $2.00
        assert pytest.approx(res.estimated_chat_input_cost, rel=1e-5) == 2.0
        assert res.formatted_estimated_cost == "$2.000000"

    def test_count_tokens_in_directory(self, tmp_path: Path):
        """Counts tokens across all .txt files in a directory."""
        (tmp_path / "doc1.txt").write_text("Hello world", encoding="utf-8")
        (tmp_path / "doc2.txt").write_text("ChronoLex compliance test", encoding="utf-8")
        (tmp_path / "ignore.pdf").write_text("Ignored binary", encoding="utf-8")

        results = count_tokens_in_directory(tmp_path)
        assert len(results) == 2
        for path_str, count in results:
            assert count > 0


# ===========================================================================
# 5. LLM Response Usage & Cost Integration Tests
# ===========================================================================


class TestLLMUsageCostEnrichment:
    """Tests for extracting usage tokens and calculating costs in LLM responses."""

    def test_token_usage_model_with_cost(self):
        """TokenUsage model retains prompt, completion, total tokens and optional cost."""
        usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            estimated_cost=0.0008,
        )
        assert usage.prompt_tokens == 1000
        assert usage.completion_tokens == 200
        assert usage.total_tokens == 1200
        assert usage.estimated_cost == 0.0008

    @patch("app.services.llm.OpenAI")
    def test_llm_service_calculates_cost_when_rates_configured(self, mock_openai_cls):
        """When LLM rates are configured, successful response computes estimated_cost."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Mock OpenAI chat completion response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Mocked regulatory analysis"))
        ]
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        )
        mock_client.chat.completions.create.return_value = mock_response

        # Instantiate service with mock client
        service = LLMService(client=mock_client)

        resp = service.send_chat_completion(
            user_message="Evaluate refund policy",
            input_price_per_1k=0.0005,
            output_price_per_1k=0.0015,
        )
        assert resp.usage is not None
        assert resp.usage.prompt_tokens == 1000
        assert resp.usage.completion_tokens == 500
        assert resp.usage.total_tokens == 1500
        # 1000/1000*0.0005 + 500/1000*0.0015 = 0.0005 + 0.00075 = 0.00125
        assert resp.usage.estimated_cost == 0.00125

    @patch("app.services.llm.OpenAI")
    def test_llm_service_no_cost_when_rates_not_configured(self, mock_openai_cls):
        """When rates are not configured, estimated_cost remains None without crashing."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        )
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(client=mock_client)
        resp = service.send_chat_completion(user_message="Query")
        assert resp.usage is not None
        assert resp.usage.estimated_cost is None

    @patch("app.services.llm.OpenAI")
    def test_llm_service_handles_missing_usage(self, mock_openai_cls):
        """When provider returns response without usage attribute, service does not crash."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(client=mock_client)
        resp = service.send_chat_completion(user_message="Query")
        assert resp.usage is None


# ===========================================================================
# 6. FastAPI Endpoint Integration Tests
# ===========================================================================


class TestTokenEstimateAPIEndpoint:
    """Tests for POST /api/llm/token-estimate."""

    def test_token_estimate_success(self, client: TestClient):
        """POST /api/llm/token-estimate returns 200 with accurate token count."""
        response = client.post(
            "/api/llm/token-estimate",
            json={"text": "What is our refund window?", "encoding": "cl100k_base"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token_count"] == 6
        assert data["encoding"] == "cl100k_base"
        assert data["text_length_chars"] == len("What is our refund window?")

    def test_token_estimate_empty_text(self, client: TestClient):
        """POST /api/llm/token-estimate handles empty text gracefully."""
        response = client.post(
            "/api/llm/token-estimate",
            json={"text": "", "encoding": "cl100k_base"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token_count"] == 0
        assert data["text_length_chars"] == 0

    def test_token_estimate_invalid_encoding(self, client: TestClient):
        """POST /api/llm/token-estimate returns 400 for unsupported encoding name."""
        response = client.post(
            "/api/llm/token-estimate",
            json={"text": "Sample text", "encoding": "unknown_enc_name"},
        )
        assert response.status_code == 400
        assert "Invalid or unsupported tokenizer encoding" in response.json()["detail"]

    def test_token_estimate_optional_fields(self, client: TestClient):
        """POST /api/llm/token-estimate returns 200 with null token_count when text omitted."""
        response = client.post("/api/llm/token-estimate", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["token_count"] is None
        assert data["text_length_chars"] is None
