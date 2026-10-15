"""Corpus-level text cleaning service for ChronoLex.

Processes document collections and file directories, applying uniform cleaning configurations
while preserving document identifiers, metadata provenance, and source files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from app.models.document import (
    CleaningConfig,
    CorpusCleaningSummary,
    Document,
    DocumentCleaningResult,
)
from app.utils.text_cleaning import clean_text

logger = logging.getLogger(__name__)


def clean_single_document(
    doc: Document,
    config: CleaningConfig | None = None,
) -> DocumentCleaningResult:
    """Applies the cleaning pipeline to a single Document instance.

    Preserves the document ID and metadata completely untouched, creating a new
    Document instance with cleaned text.

    Args:
        doc: The input Document instance.
        config: Optional cleaning configuration. Defaults to standard configuration.

    Returns:
        DocumentCleaningResult with character metrics, status, and the cleaned Document.
    """
    if config is None:
        config = CleaningConfig()

    original_length = len(doc.text) if doc.text is not None else 0

    if doc.text is None:
        return DocumentCleaningResult(
            document_id=doc.id,
            status="skipped",
            original_char_count=0,
            cleaned_char_count=0,
            char_diff=0,
            reduction_percentage=0.0,
            error_message="Document text is None",
            document=doc,
        )

    try:
        cleaned_text = clean_text(
            doc.text,
            known_boilerplate=config.known_boilerplate_patterns,
            repair_encoding_artifacts=config.repair_mojibake,
            remove_pages=config.remove_page_numbers,
            remove_boilerplate=config.remove_repeated_boilerplate,
            normalize_spaces=config.normalize_whitespace,
        )

        cleaned_length = len(cleaned_text)
        diff = original_length - cleaned_length
        pct = round((diff / original_length * 100.0), 2) if original_length > 0 else 0.0

        # Preserve metadata and ID, update text only
        cleaned_doc = Document(
            id=doc.id,
            text=cleaned_text,
            metadata=dict(doc.metadata),
        )

        return DocumentCleaningResult(
            document_id=doc.id,
            status="cleaned",
            original_char_count=original_length,
            cleaned_char_count=cleaned_length,
            char_diff=diff,
            reduction_percentage=pct,
            document=cleaned_doc,
        )
    except Exception as exc:
        logger.error("Failed to clean document %s: %s", doc.id, exc, exc_info=True)
        return DocumentCleaningResult(
            document_id=doc.id,
            status="failed",
            original_char_count=original_length,
            cleaned_char_count=original_length,
            char_diff=0,
            reduction_percentage=0.0,
            error_message=str(exc),
            document=doc,
        )


def clean_corpus(
    documents: Sequence[Document],
    config: CleaningConfig | None = None,
) -> tuple[list[Document], CorpusCleaningSummary]:
    """Applies cleaning consistently across a collection of documents.

    Handles individual document failures gracefully without corrupting others.

    Args:
        documents: Sequence of Document objects.
        config: Optional cleaning configuration.

    Returns:
        Tuple of (list of cleaned Documents, CorpusCleaningSummary with metrics).
    """
    if config is None:
        config = CleaningConfig()

    cleaned_docs: list[Document] = []
    results: list[DocumentCleaningResult] = []
    processed_count = 0
    skipped_count = 0
    failed_count = 0
    total_original = 0
    total_cleaned = 0

    for doc in documents:
        result = clean_single_document(doc, config)
        results.append(result)

        if result.status == "cleaned":
            processed_count += 1
            if result.document is not None:
                cleaned_docs.append(result.document)
            total_original += result.original_char_count
            total_cleaned += result.cleaned_char_count
        elif result.status == "skipped":
            skipped_count += 1
            if result.document is not None:
                cleaned_docs.append(result.document)
        elif result.status == "failed":
            failed_count += 1
            if result.document is not None:
                cleaned_docs.append(result.document)

    total_diff = total_original - total_cleaned
    overall_pct = (
        round((total_diff / total_original * 100.0), 2)
        if total_original > 0
        else 0.0
    )

    summary = CorpusCleaningSummary(
        total_documents=len(documents),
        processed=processed_count,
        skipped=skipped_count,
        failed=failed_count,
        total_original_chars=total_original,
        total_cleaned_chars=total_cleaned,
        total_char_reduction=total_diff,
        overall_reduction_percentage=overall_pct,
        document_results=results,
    )

    return cleaned_docs, summary


def clean_corpus_directory(
    input_dir: Path | str,
    output_dir: Path | str,
    config: CleaningConfig | None = None,
    file_extensions: tuple[str, ...] = (".txt", ".md"),
) -> CorpusCleaningSummary:
    """Cleans a directory of supported text documents and saves cleaned outputs to a separate directory.

    Safety:
    - Never overwrites source files by default.
    - Creates output directory if it does not exist.
    - Preserves file stems and relative paths where appropriate.

    Args:
        input_dir: Source directory containing raw documents.
        output_dir: Target directory for cleaned documents.
        config: Optional cleaning configuration.
        file_extensions: File extensions to process (e.g. .txt, .md).

    Returns:
        CorpusCleaningSummary with processing results and character metrics.
    """
    in_path = Path(input_dir).resolve()
    out_path = Path(output_dir).resolve()

    if not in_path.exists() or not in_path.is_dir():
        raise FileNotFoundError(f"Input directory does not exist or is not a directory: {in_path}")

    if in_path == out_path:
        raise ValueError("Input and output directories must be different to prevent overwriting source documents.")

    out_path.mkdir(parents=True, exist_ok=True)

    # Discover target files
    input_files: list[Path] = []
    for ext in file_extensions:
        input_files.extend(sorted(in_path.glob(f"*{ext}")))

    documents: list[Document] = []
    for file_path in input_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            doc = Document(
                id=file_path.name,
                text=content,
                metadata={
                    "source_path": str(file_path),
                    "filename": file_path.name,
                    "extension": file_path.suffix,
                },
            )
            documents.append(doc)
        except Exception as exc:
            logger.error("Failed to read file %s: %s", file_path, exc)
            # Create a placeholder document to track failure in summary
            doc = Document(
                id=file_path.name,
                text="",
                metadata={"source_path": str(file_path), "error": str(exc)},
            )
            documents.append(doc)

    cleaned_docs, summary = clean_corpus(documents, config)

    # Write cleaned documents to output directory
    for doc in cleaned_docs:
        out_file = out_path / doc.id
        out_file.write_text(doc.text, encoding="utf-8")

    return summary
