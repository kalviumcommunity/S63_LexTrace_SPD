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
