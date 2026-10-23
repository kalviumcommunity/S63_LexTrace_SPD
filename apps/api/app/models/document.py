"""Pydantic data models for documents, text cleaning configurations, and corpus processing results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Core document representation for ChronoLex ingestion and RAG pipeline.

    Attributes:
        id: Unique identifier for the document (e.g., circular ID, hash, or filename).
        text: Extracted raw or cleaned text content.
        metadata: Key-value attributes preserving provenance, circular numbers, dates, and authorities.
    """

    id: str = Field(..., description="Unique document identifier.")
    text: str = Field(..., description="Document text content.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary provenance, temporal, and classification metadata.",
    )


class CleaningConfig(BaseModel):
    """Configuration options for text cleaning and boilerplate removal."""

    normalize_unicode: bool = Field(
        default=True,
        description="Whether to apply Unicode NFKC normalization and line ending standardization.",
    )
    repair_mojibake: bool = True
    remove_page_numbers: bool = Field(
        default=True,
        description="Whether to remove standalone page-number lines (e.g. 'Page 3 of 12').",
    )
    remove_repeated_boilerplate: bool = Field(
        default=True,
        description="Whether to remove repeated headers, footers, and configured boilerplate patterns.",
    )
    normalize_whitespace: bool = Field(
        default=True,
        description="Whether to collapse consecutive spaces/tabs and excessive blank lines.",
    )
    known_boilerplate_patterns: List[str] = Field(
        default_factory=list,
        description="Custom list of regex patterns or exact string phrases representing recurring noise.",
    )
    min_header_footer_repetitions: int = Field(
        default=2,
        ge=2,
        description="Minimum page repetitions required to classify a header/footer candidate.",
    )


class DocumentCleaningResult(BaseModel):
    """Result and character metrics for an individual cleaned document."""

    document_id: str
    status: str = Field(
        ...,
        description="Processing status: 'cleaned', 'skipped', or 'failed'.",
    )
    original_char_count: int = Field(default=0, ge=0)
    cleaned_char_count: int = Field(default=0, ge=0)
    char_diff: int = Field(default=0, description="original_char_count - cleaned_char_count")
    reduction_percentage: float = Field(
        default=0.0,
        description="Percentage of characters removed during cleaning.",
    )
    error_message: Optional[str] = None
    document: Optional[Document] = Field(
        default=None,
        description="Cleaned Document object with updated text and preserved metadata.",
    )


class CorpusCleaningSummary(BaseModel):
    """Corpus-level statistics and reporting for batch cleaning operations."""

    total_documents: int = Field(default=0, ge=0)
    processed: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    total_original_chars: int = Field(default=0, ge=0)
    total_cleaned_chars: int = Field(default=0, ge=0)
    total_char_reduction: int = Field(default=0, ge=0)
    overall_reduction_percentage: float = Field(default=0.0)
    document_results: List[DocumentCleaningResult] = Field(default_factory=list)


class ChunkConfig(BaseModel):
    """Configuration for token-aware document chunking."""

    chunk_size: int = Field(
        default=400,
        gt=0,
        description="Maximum number of tokens per chunk.",
    )
    chunk_overlap: int = Field(
        default=60,
        ge=0,
        description="Number of boundary tokens repeated across adjacent chunks.",
    )
    encoding_name: str = Field(
        default="cl100k_base",
        description="Tokenizer encoding name (e.g. cl100k_base).",
    )


class DocumentChunk(Document):
    """A token-sized chunk of a parent document with preserved metadata and provenance.

    Inherits from Document so it adheres to the core document schema with id, text, and metadata.
    """

    document_id: str = Field(
        ...,
        description="ID of the source document from which this chunk was derived.",
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="0-based sequence index of the chunk within the source document.",
    )
    total_chunks: int = Field(
        default=1,
        ge=1,
        description="Total number of chunks produced from the source document.",
    )
    token_count: int = Field(
        default=0,
        ge=0,
        description="Actual token count of this chunk.",
    )
    start_token_idx: int = Field(
        default=0,
        ge=0,
        description="Start offset of the chunk in the document's token sequence.",
    )
    end_token_idx: int = Field(
        default=0,
        ge=0,
        description="End offset of the chunk in the document's token sequence.",
    )


class CorpusChunkingSummary(BaseModel):
    """Corpus-level statistics and reporting for batch chunking operations."""

    total_documents: int = Field(default=0, ge=0)
    total_chunks: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    avg_tokens_per_chunk: float = Field(default=0.0)
    chunk_size: int = Field(default=400, gt=0)
    chunk_overlap: int = Field(default=60, ge=0)
    encoding_name: str = Field(default="cl100k_base")
    chunks: List[DocumentChunk] = Field(default_factory=list)


class ChunkRequest(BaseModel):
    """API request model for token-aware chunking."""

    text: str = Field(..., description="Text content to split into chunks.")
    chunk_size: int = Field(default=400, gt=0, description="Max tokens per chunk.")
    chunk_overlap: int = Field(default=60, ge=0, description="Token overlap between adjacent chunks.")
    encoding_name: str = Field(default="cl100k_base", description="Tokenizer encoding name.")
    clean_first: bool = Field(default=False, description="Whether to apply conservative text cleaning first.")


class ChunkResponse(BaseModel):
    """API response model for token-aware chunking."""

    total_chunks: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    chunk_size: int = Field(default=400)
    chunk_overlap: int = Field(default=60)
    encoding_name: str = Field(default="cl100k_base")
    chunks: List[str] = Field(default_factory=list)
    chunk_details: List[Dict[str, Any]] = Field(default_factory=list)

