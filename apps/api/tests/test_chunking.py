"""Comprehensive automated tests for ChronoLex Token-Aware Chunking & Overlap.

Verifies:
- Empty, None, and whitespace-only text handling (returns empty list).
- Single chunk behavior for texts fitting within token size limits.
- Multi-chunk generation and token-count limits for every chunk under tiktoken.
- Correct overlap behavior between adjacent chunks using token-level slice equality.
- Zero-overlap behavior (adjacent chunks are strictly contiguous partitions).
- Validation of negative/zero chunk sizes and negative/excessive overlaps.
- Unsupported tokenizer encoding rejection with clear ValueErrors.
- Deterministic chunking across repeated identical calls.
- Preservation of document ID, citation, and provenance metadata in DocumentChunk records.
- Comparative token statistics (Configuration A vs. Configuration B).
- Boundary-context preservation across the committed regulatory sample.
- API endpoint integration for POST /api/llm/chunk.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.models.document import ChunkConfig, Document, DocumentChunk
from app.utils.chunking import (
    chunk_corpus,
    chunk_document,
    chunk_file,
    token_chunks,
    token_chunks_detailed,
)
from app.utils.tokenization import get_tokenizer

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SAMPLE_PATH = PROJECT_ROOT / "data" / "examples" / "chunking_sample.txt"


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


# ===========================================================================
# 1. Edge Case Handling & Input Validation
# ===========================================================================


class TestInputValidationAndEdgeCases:
    """Tests input sanitation, parameter boundary validation, and encoding checks."""

    def test_empty_and_whitespace_input(self):
        """None, empty string, and whitespace-only strings must return empty lists."""
        assert token_chunks("") == []
        assert token_chunks(None) == []
        assert token_chunks("   \n\t  \n") == []
        assert token_chunks_detailed("") == []
        assert token_chunks_detailed("   ") == []

    def test_invalid_chunk_size(self):
        """Chunk size <= 0 must raise ValueError."""
        with pytest.raises(ValueError, match="Chunk size must be a positive integer"):
            token_chunks("Sample text", size=0, overlap=0)

        with pytest.raises(ValueError, match="Chunk size must be a positive integer"):
            token_chunks("Sample text", size=-10, overlap=0)

    def test_invalid_overlap(self):
        """Overlap < 0 or overlap >= size must raise ValueError."""
        with pytest.raises(ValueError, match="Overlap must be a non-negative integer"):
            token_chunks("Sample text", size=100, overlap=-5)

        with pytest.raises(ValueError, match="Overlap .* must be strictly smaller than chunk size"):
            token_chunks("Sample text", size=100, overlap=100)

        with pytest.raises(ValueError, match="Overlap .* must be strictly smaller than chunk size"):
            token_chunks("Sample text", size=100, overlap=120)

    def test_invalid_encoding(self):
        """Invalid or unsupported encoding names must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid or unsupported tokenizer encoding"):
            token_chunks("Sample text", encoding="non_existent_tokenizer_xyz")


# ===========================================================================
# 2. Token Boundaries, Slicing, and Overlap Logic
# ===========================================================================


class TestTokenChunkingLogic:
    """Tests token-based slicing, limits, overlap verification, and determinism."""

    def test_single_chunk_fit(self):
        """Text whose token count is <= size must produce exactly one chunk."""
        text = "Reserve Bank of India Master Direction on KYC/AML wire transfer verification."
        enc = get_tokenizer("cl100k_base")
        token_count = len(enc.encode(text))

        chunks = token_chunks(text, size=token_count + 50, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_token_limits(self):
        """Every generated chunk must have <= size tokens under the tokenizer."""
        # Generate multi-sentence repeating text
        sentence = "All Regulated Entities must verify originator details under Section 35A. "
        text = sentence * 40  # ~400 tokens

        chunks = token_chunks(text, size=100, overlap=20)
        enc = get_tokenizer("cl100k_base")

        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            count = len(enc.encode(chunk))
            assert count <= 100, f"Chunk {i} exceeded limit: {count} > 100"

    def test_token_overlap_exact_slice_match(self):
        """Adjacent chunks must repeat the exact final N tokens of the preceding chunk."""
        sentence = "Compliance audit requirement for high risk correspondent banking corridors. "
        text = sentence * 30
        enc = get_tokenizer("cl100k_base")

        overlap = 25
        size = 120
        detailed = token_chunks_detailed(text, size=size, overlap=overlap)

        assert len(detailed) >= 3

        for i in range(len(detailed) - 1):
            curr_chunk = detailed[i]
            next_chunk = detailed[i + 1]

            # The last `overlap` tokens of curr_chunk must match the first `overlap` tokens of next_chunk
            curr_tail_tokens = curr_chunk["tokens"][-overlap:]
            next_head_tokens = next_chunk["tokens"][:overlap]

            assert curr_tail_tokens == next_head_tokens, (
                f"Mismatch in overlap between chunk {i} and {i+1}: "
                f"{curr_tail_tokens} != {next_head_tokens}"
            )

    def test_zero_overlap_contiguous_partition(self):
        """When overlap=0, tokens across all chunks must reconstruct the original token stream."""
        sentence = "Notice of penal provisions under the Banking Regulation Act Section 47A. "
        text = sentence * 25
        enc = get_tokenizer("cl100k_base")
        original_tokens = enc.encode(text)

        size = 80
        detailed = token_chunks_detailed(text, size=size, overlap=0)
        concatenated_tokens = []
        for c in detailed:
            concatenated_tokens.extend(c["tokens"])

        assert concatenated_tokens == original_tokens

    def test_deterministic_output(self):
        """Identical inputs and settings must yield identical chunks."""
        text = "Deterministic chunking verification for ChronoLex RAG compliance engine." * 15
        run1 = token_chunks(text, size=50, overlap=10)
        run2 = token_chunks(text, size=50, overlap=10)
        assert run1 == run2


# ===========================================================================
# 3. Document Integration & Provenance Metadata
# ===========================================================================


class TestDocumentIntegration:
    """Verifies Document, DocumentChunk, CorpusChunkingSummary, and metadata preservation."""

    def test_document_chunk_provenance(self):
        """DocumentChunk instances must retain document ID, metadata, and citation info."""
        doc = Document(
            id="RBI_CIRCULAR_2024_01",
            text="Section 1. Scope.\n" + ("Compliance rule directive text. " * 50),
            metadata={
                "authority": "Reserve Bank of India",
                "circular_no": "RBI/2024-25/108",
                "date": "2024-04-01",
            },
        )

        config = ChunkConfig(chunk_size=100, chunk_overlap=20)
        chunks = chunk_document(doc, config=config, clean_first=False)

        assert len(chunks) > 1
        for idx, chunk in enumerate(chunks):
            assert isinstance(chunk, DocumentChunk)
            assert chunk.document_id == "RBI_CIRCULAR_2024_01"
            assert chunk.chunk_index == idx
            assert chunk.total_chunks == len(chunks)
            assert chunk.id == f"RBI_CIRCULAR_2024_01_chunk_{idx}"
            assert chunk.token_count <= 100

            # Verify original metadata is preserved and provenance is appended
            assert chunk.metadata["authority"] == "Reserve Bank of India"
            assert chunk.metadata["circular_no"] == "RBI/2024-25/108"
            assert chunk.metadata["source_document_id"] == "RBI_CIRCULAR_2024_01"
            assert chunk.metadata["chunk_index"] == idx

    def test_chunk_corpus_summary(self):
        """Batch corpus chunking must compute aggregate statistics across documents."""
        docs = [
            Document(id="doc_1", text="First policy text content. " * 30),
            Document(id="doc_2", text="Second policy text content. " * 40),
        ]

        config = ChunkConfig(chunk_size=120, chunk_overlap=25)
        summary = chunk_corpus(docs, config=config, clean_first=False)

        assert summary.total_documents == 2
        assert summary.total_chunks > 2
        assert summary.total_tokens == sum(c.token_count for c in summary.chunks)
        assert summary.avg_tokens_per_chunk > 0

    def test_chunk_file(self, tmp_path: Path):
        """chunk_file must read a target file and return DocumentChunks."""
        test_file = tmp_path / "test_reg.txt"
        test_file.write_text("Legislative mandates and compliance protocols. " * 40, encoding="utf-8")

        chunks = chunk_file(test_file, config=ChunkConfig(chunk_size=100, chunk_overlap=15))
        assert len(chunks) > 1
        assert chunks[0].document_id == "test_reg.txt"
        assert chunks[0].metadata["source_filename"] == "test_reg.txt"


# ===========================================================================
# 4. Realistic Regulatory Sample & Boundary Behavior
# ===========================================================================


class TestSampleRegulatoryBenchmark:
    """Tests the committed sample and verifies boundary-context preservation."""

    def test_committed_sample_file_exists(self):
        """Committed sample file must exist and contain substantial content."""
        assert SAMPLE_PATH.is_file(), f"Sample file not found at {SAMPLE_PATH}"
        text = SAMPLE_PATH.read_text(encoding="utf-8")
        assert len(text) > 2000

    def test_configuration_a_vs_b_statistics(self):
        """Verifies chunk count, total tokens, and overlap expansion between Config A and B."""
        text = SAMPLE_PATH.read_text(encoding="utf-8")
        enc = get_tokenizer("cl100k_base")
        orig_tokens = len(enc.encode(text))

        # Config A (400 / 0)
        chunks_a = token_chunks_detailed(text, size=400, overlap=0)
        total_tokens_a = sum(c["token_count"] for c in chunks_a)

        # Config B (400 / 60)
        chunks_b = token_chunks_detailed(text, size=400, overlap=60)
        total_tokens_b = sum(c["token_count"] for c in chunks_b)

        # Both must produce multiple chunks
        assert len(chunks_a) == 2
        assert len(chunks_b) == 2

        # Config A tokens must equal original tokens
        assert total_tokens_a == orig_tokens

        # Config B must introduce exactly 60 duplicated overlap tokens
        assert total_tokens_b == total_tokens_a + 60

        # Every chunk must be strictly <= 400 tokens
        for c in chunks_a:
            assert c["token_count"] <= 400
        for c in chunks_b:
            assert c["token_count"] <= 400

    def test_boundary_context_preservation_demonstration(self):
        """Demonstrates that a regulatory exception clause split in Config A is preserved in Config B."""
        text = SAMPLE_PATH.read_text(encoding="utf-8")

        # Config A (no overlap):
        chunks_a = token_chunks(text, size=400, overlap=0)
        c0_a = chunks_a[0]
        c1_a = chunks_a[1]

        # In Config A, the word 'UNLESS' is severed across the chunk boundary:
        # c0 ends with '...UNLESS the transferring institution'
        # c1 begins with ' obtains a verified statutory clearance certificate...'
        assert "UNLESS the transferring institution" in c0_a
        assert "obtains a verified statutory clearance certificate" in c1_a

        # Config B (60 tokens overlap):
        chunks_b = token_chunks(text, size=400, overlap=60)
        c1_b = chunks_b[1]

        # In Config B, Chunk 2 contains BOTH the prohibition context and the exception clause:
        assert "strictly prohibited from executing wire transfers linked to designated jurisdictions" in c1_b
        assert "UNLESS the transferring institution" in c1_b
        assert "obtains a verified statutory clearance certificate" in c1_b


# ===========================================================================
# 5. API Endpoint Tests (POST /api/llm/chunk)
# ===========================================================================


class TestChunkApiEndpoint:
    """Verifies FastAPI endpoint integration for token-aware chunking."""

    def test_chunk_endpoint_success(self, client: TestClient):
        """Endpoint must return 200 with structured chunks and token counts."""
        payload = {
            "text": "Regulatory rule statement. " * 30,
            "chunk_size": 100,
            "chunk_overlap": 20,
            "encoding_name": "cl100k_base",
        }
        response = client.post("/api/llm/chunk", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["total_chunks"] > 1
        assert data["total_tokens"] > 0
        assert len(data["chunks"]) == data["total_chunks"]
        assert len(data["chunk_details"]) == data["total_chunks"]

    def test_chunk_endpoint_validation_error(self, client: TestClient):
        """Endpoint must reject invalid chunk sizes or overlap with 400/422."""
        # Overlap >= size
        payload = {
            "text": "Sample text",
            "chunk_size": 50,
            "chunk_overlap": 60,
        }
        response = client.post("/api/llm/chunk", json=payload)
        assert response.status_code == 400

        # Chunk size <= 0
        payload_invalid_size = {
            "text": "Sample text",
            "chunk_size": 0,
            "chunk_overlap": 0,
        }
        response = client.post("/api/llm/chunk", json=payload_invalid_size)
        assert response.status_code in (400, 422)
