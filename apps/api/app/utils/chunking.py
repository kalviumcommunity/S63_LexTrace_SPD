"""Token-aware chunking utilities for ChronoLex document processing.

Provides:
- Token-based text splitting with controlled overlap using tiktoken.
- Verification and enforcement of tokenizer boundary limits.
- Guaranteed forward progress, deterministic execution, and zero-length input resilience.
- Integration with Document and DocumentChunk schemas, preserving metadata and citations.
- Corpus and batch document processing helpers.

Important Limitation Note:
Token boundaries are determined by Byte-Pair Encoding (BPE) subword merges and do not
necessarily align with natural language boundaries (words, punctuation, or sentences).
Token-based slicing alone cannot guarantee grammatically complete sentences. Controlled
overlap helps mitigate split-sentence context loss across adjacent chunks, but chunking
settings must be paired with upstream text cleaning and downstream retrieval evaluation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import tiktoken

from app.models.document import (
    ChunkConfig,
    CleaningConfig,
    CorpusChunkingSummary,
    Document,
    DocumentChunk,
)
from app.utils.tokenization import DEFAULT_ENCODING, get_tokenizer

logger = logging.getLogger(__name__)


def token_chunks(
    text: Optional[str],
    size: int = 400,
    overlap: int = 60,
    encoding: str = DEFAULT_ENCODING,
) -> List[str]:
    """Splits text into token-sized chunks with controlled token overlap.

    Slices text based on exact token boundaries using tiktoken, ensuring that
    no individual chunk exceeds `size` tokens, and that adjacent chunks repeat
    the final `overlap` tokens from the preceding chunk.

    Args:
        text: Input text to chunk. If None, empty, or whitespace-only, returns an empty list.
        size: Maximum number of tokens per chunk. Must be a positive integer.
        overlap: Number of tokens repeated between adjacent chunks. Must be non-negative
            and strictly less than size.
        encoding: Tiktoken tokenizer encoding name (default: "cl100k_base").

    Returns:
        List of decoded text strings, each containing at most `size` tokens.

    Raises:
        ValueError: If size <= 0, overlap < 0, overlap >= size, or encoding is unsupported.
    """
    if size <= 0:
        raise ValueError(f"Chunk size must be a positive integer, got {size}.")
    if overlap < 0:
        raise ValueError(f"Overlap must be a non-negative integer, got {overlap}.")
    if overlap >= size:
        raise ValueError(
            f"Overlap ({overlap}) must be strictly smaller than chunk size ({size})."
        )

    if text is None or not str(text).strip():
        return []

    enc = get_tokenizer(encoding)
    tokens = enc.encode(text)
    total_tokens = len(tokens)

    if total_tokens == 0:
        return []

    # Single chunk case: text fits entirely within one chunk limit
    if total_tokens <= size:
        return [enc.decode(tokens, errors="replace")]

    step = size - overlap
    chunks: List[str] = []
    start = 0

    while start < total_tokens:
        end = min(start + size, total_tokens)
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens, errors="replace"))
        if end >= total_tokens:
            break
        start += step

    return chunks


def token_chunks_detailed(
    text: Optional[str],
    size: int = 400,
    overlap: int = 60,
    encoding: str = DEFAULT_ENCODING,
) -> List[Dict[str, Any]]:
    """Splits text into chunks and returns structured token metrics for each chunk.

    Args:
        text: Input text to chunk.
        size: Target token size per chunk.
        overlap: Token overlap between adjacent chunks.
        encoding: Tiktoken tokenizer encoding name.

    Returns:
        List of dictionaries with chunk metadata:
        - chunk_index: 0-based position
        - text: Decoded chunk text
        - token_count: Number of tokens in this chunk
        - start_token_idx: Offset of the first token in the source token stream
        - end_token_idx: Offset of the last token in the source token stream
        - tokens: Raw integer token ID list
    """
    if size <= 0:
        raise ValueError(f"Chunk size must be a positive integer, got {size}.")
    if overlap < 0:
        raise ValueError(f"Overlap must be a non-negative integer, got {overlap}.")
    if overlap >= size:
        raise ValueError(
            f"Overlap ({overlap}) must be strictly smaller than chunk size ({size})."
        )

    if text is None or not str(text).strip():
        return []

    enc = get_tokenizer(encoding)
    tokens = enc.encode(text)
    total_tokens = len(tokens)

    if total_tokens == 0:
        return []

    if total_tokens <= size:
        return [
            {
                "chunk_index": 0,
                "text": enc.decode(tokens, errors="replace"),
                "token_count": total_tokens,
                "start_token_idx": 0,
                "end_token_idx": total_tokens,
                "tokens": tokens,
            }
        ]

    step = size - overlap
    detailed_chunks: List[Dict[str, Any]] = []
    start = 0
    idx = 0

    while start < total_tokens:
        end = min(start + size, total_tokens)
        chunk_tokens = tokens[start:end]
        decoded = enc.decode(chunk_tokens, errors="replace")
        detailed_chunks.append(
            {
                "chunk_index": idx,
                "text": decoded,
                "token_count": len(chunk_tokens),
                "start_token_idx": start,
                "end_token_idx": end,
                "tokens": chunk_tokens,
            }
        )
        idx += 1
        if end >= total_tokens:
            break
        start += step

    return detailed_chunks


def chunk_document(
    doc: Document,
    config: Optional[ChunkConfig] = None,
    clean_first: bool = True,
    cleaning_config: Optional[CleaningConfig] = None,
) -> List[DocumentChunk]:
    """Splits a Document into token-bounded DocumentChunk instances.

    Preserves parent document identifiers, provenance metadata, citations, and adds
    chunk-level coordinates (chunk_index, total_chunks, start_token_idx, end_token_idx).

    Args:
        doc: The source Document instance.
        config: Chunking configuration (chunk_size, chunk_overlap, encoding_name).
        clean_first: Whether to apply the text cleaning pipeline before chunking.
        cleaning_config: Optional text cleaning settings when clean_first is True.

    Returns:
        List of DocumentChunk instances derived from the source document.
    """
    if config is None:
        config = ChunkConfig()

    text_to_chunk = doc.text or ""
    if clean_first and text_to_chunk.strip():
        from app.utils.text_cleaning import clean_text

        known_patterns = cleaning_config.known_boilerplate_patterns if cleaning_config else []
        text_to_chunk = clean_text(text_to_chunk, known_boilerplate=known_patterns)

    raw_details = token_chunks_detailed(
        text=text_to_chunk,
        size=config.chunk_size,
        overlap=config.chunk_overlap,
        encoding=config.encoding_name,
    )

    total_chunks = len(raw_details)
    if total_chunks == 0:
        return []

    chunks: List[DocumentChunk] = []
    for detail in raw_details:
        idx = detail["chunk_index"]
        # Deepcopy or enrich source metadata with chunk provenance
        chunk_meta = dict(doc.metadata)
        chunk_meta.update(
            {
                "source_document_id": doc.id,
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "chunk_token_count": detail["token_count"],
                "start_token_idx": detail["start_token_idx"],
                "end_token_idx": detail["end_token_idx"],
                "chunk_size_configured": config.chunk_size,
                "chunk_overlap_configured": config.chunk_overlap,
                "encoding_name": config.encoding_name,
            }
        )

        chunk_id = f"{doc.id}_chunk_{idx}"
        chunk = DocumentChunk(
            id=chunk_id,
            document_id=doc.id,
            chunk_index=idx,
            total_chunks=total_chunks,
            text=detail["text"],
            token_count=detail["token_count"],
            start_token_idx=detail["start_token_idx"],
            end_token_idx=detail["end_token_idx"],
            metadata=chunk_meta,
        )
        chunks.append(chunk)

    return chunks


def chunk_corpus(
    documents: Sequence[Document],
    config: Optional[ChunkConfig] = None,
    clean_first: bool = True,
    cleaning_config: Optional[CleaningConfig] = None,
) -> CorpusChunkingSummary:
    """Processes a collection of Documents into token-bounded DocumentChunks.

    Args:
        documents: Collection of Document instances.
        config: Chunking configuration.
        clean_first: Whether to clean document text before chunking.
        cleaning_config: Optional cleaning configuration.

    Returns:
        CorpusChunkingSummary with aggregate token counts, chunk metrics, and chunks.
    """
    if config is None:
        config = ChunkConfig()

    all_chunks: List[DocumentChunk] = []
    for doc in documents:
        doc_chunks = chunk_document(
            doc=doc,
            config=config,
            clean_first=clean_first,
            cleaning_config=cleaning_config,
        )
        all_chunks.extend(doc_chunks)

    total_tokens = sum(c.token_count for c in all_chunks)
    total_chunks = len(all_chunks)
    avg_tokens = round(total_tokens / total_chunks, 2) if total_chunks > 0 else 0.0

    return CorpusChunkingSummary(
        total_documents=len(documents),
        total_chunks=total_chunks,
        total_tokens=total_tokens,
        avg_tokens_per_chunk=avg_tokens,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        encoding_name=config.encoding_name,
        chunks=all_chunks,
    )


def chunk_file(
    file_path: Union[str, Path],
    config: Optional[ChunkConfig] = None,
    clean_first: bool = True,
    cleaning_config: Optional[CleaningConfig] = None,
    doc_id: Optional[str] = None,
) -> List[DocumentChunk]:
    """Reads a text file and chunks its contents into DocumentChunks.

    Args:
        file_path: Path to the target text file.
        config: Chunking configuration.
        clean_first: Whether to clean text before chunking.
        cleaning_config: Optional cleaning configuration.
        doc_id: Optional document ID override. Defaults to file name.

    Returns:
        List of DocumentChunk instances.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Target document file not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    effective_id = doc_id or path.name

    doc = Document(
        id=effective_id,
        text=text,
        metadata={
            "source_filename": path.name,
            "source_path": str(path.resolve()),
            "source_filesize_bytes": path.stat().st_size,
        },
    )

    return chunk_document(
        doc=doc,
        config=config,
        clean_first=clean_first,
        cleaning_config=cleaning_config,
    )
