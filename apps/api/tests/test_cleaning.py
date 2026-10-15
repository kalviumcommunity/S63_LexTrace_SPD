"""Automated test suite for ChronoLex text extraction, cleaning, and normalization pipeline.

Verifies:
- Unicode NFKC normalization (ligatures, full-width characters).
- Windows CRLF and legacy CR line ending standardization to LF.
- Consecutive space, tab, and excessive newline collapse while preserving paragraph boundaries.
- Standalone page-number removal (Page X of Y, Page X, - Page X -, [Page X], etc.) without corrupting inline text.
- Repeated boilerplate and header/footer removal across pages.
- Configurable known boilerplate pattern removal.
- Safe mojibake repair without blind document re-encoding.
- Preservation of regulatory identifiers, section numbers, dates, monetary amounts, and table structures.
- Preservation of legitimate repeating phrases and headings when not in header/footer zones.
- Handling of empty strings, whitespace-only strings, and invalid input types.
- Deterministic cleaning output across repeated runs.
- Document ID and metadata immutability during corpus processing.
- Batch processing across document collections and directory text files.
- Preservation of raw source files on disk.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from app.models.document import CleaningConfig, Document
from app.services.corpus_cleaner import (
    clean_corpus,
    clean_corpus_directory,
    clean_single_document,
)
from app.utils.text_cleaning import (
    PAGE_NUMBER_LINE_REGEX,
    clean_text,
    detect_repeated_headers_footers,
    normalize_unicode_and_newlines,
    normalize_whitespace,
    remove_page_numbers,
    remove_repeated_boilerplate,
    repair_mojibake,
)


class TestUnicodeAndLineEndingNormalization:
    """Verifies Unicode NFKC, line endings, non-breaking spaces, and mojibake repairs."""

    def test_empty_and_whitespace_input(self) -> None:
        assert clean_text("") == ""
        assert clean_text("   \n\t\n   ") == ""
        assert normalize_unicode_and_newlines("") == ""

    def test_invalid_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected str"):
            clean_text(None)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Expected str"):
            normalize_unicode_and_newlines(123)  # type: ignore[arg-type]

    def test_windows_crlf_and_cr_to_unix_lf(self) -> None:
        raw = "Line 1\r\nLine 2\rLine 3\nLine 4"
        normalized = normalize_unicode_and_newlines(raw)
        assert "\r" not in normalized
        assert normalized == "Line 1\nLine 2\nLine 3\nLine 4"

    def test_nfkc_normalization(self) -> None:
        # Compatibility ligature 'ﬁ' -> 'fi', fullwidth 'Ａ' -> 'A'
        raw = "ﬁnancial regulation ＡＢＣ"
        cleaned = normalize_unicode_and_newlines(raw)
        assert cleaned == "financial regulation ABC"

    def test_non_breaking_spaces_and_zero_width_chars(self) -> None:
        # \u00a0 is NBSP, \u200b is zero-width space
        raw = "Section\u00a03.1:\u200b Capital\u202fAdequacy"
        cleaned = normalize_unicode_and_newlines(raw)
        assert cleaned == "Section 3.1: Capital Adequacy"

    def test_safe_mojibake_repairs(self) -> None:
        raw = "The bankâ€™s risk committee reviewed the directorâ€™s â€œspecial reportâ€\x9d."
        cleaned = repair_mojibake(raw)
        assert cleaned == "The bank’s risk committee reviewed the director’s “special report”."

    def test_no_blind_reencoding_corruptions(self) -> None:
        # Standard UTF-8 characters should not be corrupted
        valid_text = "The borrower’s liability is €50,000 under § 4(a)."
        cleaned = normalize_unicode_and_newlines(valid_text)
        assert "borrower’s" in cleaned
        assert "€50,000" in cleaned
        assert "§ 4(a)" in cleaned


class TestPageNumberBoilerplateRemoval:
    """Verifies standalone page number stripping while preserving inline mentions."""

    @pytest.mark.parametrize(
        "page_line",
        [
            "Page 1",
            "page 12",
            "Page 3 of 12",
            "Page 4 / 20",
            "- Page 4 of 20 -",
            "— Page 5 —",
            "[Page 2]",
            "  Page 10 of 100  ",
            "pg. 7",
            "p. 14",
            "- 12 -",
            "[12]",
        ],
    )
    def test_page_number_line_regex_matches(self, page_line: str) -> None:
        assert PAGE_NUMBER_LINE_REGEX.match(page_line) is not None

    def test_remove_standalone_page_numbers(self) -> None:
        text = (
            "Header Content\n"
            "Page 1 of 5\n"
            "Section 1. Requirements\n"
            "- Page 2 of 5 -\n"
            "Section 2. Conclusion\n"
            "[Page 3]"
        )
        cleaned = remove_page_numbers(text)
        assert "Page 1 of 5" not in cleaned
        assert "- Page 2 of 5 -" not in cleaned
        assert "[Page 3]" not in cleaned
        assert "Section 1. Requirements" in cleaned
        assert "Section 2. Conclusion" in cleaned

    def test_preserve_inline_page_mentions(self) -> None:
        text = (
            "Please refer to Page 3 of 12 in Circular RBI/2024/09.\n"
            "Section 4: Page limits shall not exceed twenty pages."
        )
        cleaned = remove_page_numbers(text)
        assert "refer to Page 3 of 12" in cleaned
        assert "Section 4: Page limits" in cleaned


class TestBoilerplateAndHeaderFooterRemoval:
    """Verifies repeated header/footer detection and custom boilerplate filtering."""

    def test_multi_page_repeated_header_detection(self) -> None:
        # 3 pages separated by form-feed \x0c
        doc = (
            "CHRONOLEX REGULATORY DIRECTIVE - CONFIDENTIAL\n"
            "Content of Page 1\n"
            "\x0c"
            "CHRONOLEX REGULATORY DIRECTIVE - CONFIDENTIAL\n"
            "Content of Page 2\n"
            "\x0c"
            "CHRONOLEX REGULATORY DIRECTIVE - CONFIDENTIAL\n"
            "Content of Page 3\n"
        )
        cleaned = remove_repeated_boilerplate(doc, min_repetitions=2)
        assert "CHRONOLEX REGULATORY DIRECTIVE - CONFIDENTIAL" not in cleaned
        assert "Content of Page 1" in cleaned
        assert "Content of Page 2" in cleaned
        assert "Content of Page 3" in cleaned

    def test_preserves_legitimate_repeated_headings_without_page_markers(self) -> None:
        # Legitimate repeated section titles across a document with no page boundaries
        doc = (
            "Section 1. Compliance Obligations\n"
            "Rule details here.\n\n"
            "Section 2. Risk Metrics\n"
            "Rule details here.\n\n"
            "Section 1. Compliance Obligations\n"
            "Addendum details here."
        )
        # Without page boundaries, conservative cleaning does not guess or delete repeated text
        cleaned = remove_repeated_boilerplate(doc)
        assert cleaned.count("Section 1. Compliance Obligations") == 2

    def test_custom_known_boilerplate_removal(self) -> None:
        text = (
            "CONFIDENTIAL - INTERNAL BANK USE ONLY\n"
            "Directive text begins here.\n"
            "VISIT HTTPS://WWW.RBI.ORG.IN FOR UPDATES\n"
            "Directive text continues."
        )
        cleaned = remove_repeated_boilerplate(
            text,
            known_boilerplate=[
                r"^CONFIDENTIAL - INTERNAL BANK USE ONLY$",
                r"VISIT HTTPS://WWW\.RBI\.ORG\.IN FOR UPDATES",
            ],
        )
        assert "CONFIDENTIAL - INTERNAL BANK USE ONLY" not in cleaned
        assert "VISIT HTTPS://WWW.RBI.ORG.IN FOR UPDATES" not in cleaned
        assert "Directive text begins here." in cleaned
        assert "Directive text continues." in cleaned


class TestWhitespaceNormalization:
    """Verifies structural whitespace collapsing and paragraph preservation."""

    def test_collapse_spaces_and_tabs(self) -> None:
        raw = "This   is    a \t\t  line   with   excessive    spacing."
        cleaned = normalize_whitespace(raw)
        assert cleaned == "This is a line with excessive spacing."

    def test_collapse_excessive_newlines(self) -> None:
        raw = "Paragraph 1\n\n\n\n\nParagraph 2\n\n\n\nParagraph 3"
        cleaned = normalize_whitespace(raw)
        assert cleaned == "Paragraph 1\n\nParagraph 2\n\nParagraph 3"

    def test_preserve_list_and_table_structure(self) -> None:
        table_text = (
            "| Tier | Ratio |\n"
            "| T1   | 8.5%  |\n"
            "| T2   | 2.0%  |\n\n"
            "1. First requirement\n"
            "2. Second requirement"
        )
        cleaned = normalize_whitespace(table_text)
        assert "| Tier | Ratio |" in cleaned
        assert "1. First requirement" in cleaned
        assert "2. Second requirement" in cleaned


class TestEndToEndCleanText:
    """Verifies end-to-end clean_text function and determinism."""

    def test_deterministic_output(self) -> None:
        noisy = (
            "CHRONOLEX AUDIT DIRECTIVE\r\n\r\n"
            "Section 4.1: The bankâ€™s capital buffer shall be 2.5%.\r\n"
            "   \r\n\r\n"
            "Page 1 of 2\r\n"
            "\x0c"
            "CHRONOLEX AUDIT DIRECTIVE\r\n\r\n"
            "Section 4.2: Audit reports are due on 2025-06-30.\r\n"
            "Page 2 of 2"
        )
        res1 = clean_text(noisy)
        res2 = clean_text(noisy)
        res3 = clean_text(noisy)
        assert res1 == res2 == res3

        # Check preserved elements
        assert "Section 4.1: The bank’s capital buffer shall be 2.5%." in res1
        assert "Section 4.2: Audit reports are due on 2025-06-30." in res1
        # Check removed noise
        assert "Page 1 of 2" not in res1
        assert "Page 2 of 2" not in res1
        assert "CHRONOLEX AUDIT DIRECTIVE" not in res1


class TestCorpusProcessingService:
    """Verifies corpus-level batch cleaning and metadata preservation."""

    def test_clean_single_document_preserves_metadata(self) -> None:
        doc = Document(
            id="circular_001",
            text="Section  1.  Scope   of Directive.\r\n\r\nPage 1",
            metadata={
                "authority": "RBI",
                "circular_no": "2024/01",
                "effective_date": "2024-04-01",
            },
        )
        result = clean_single_document(doc)
        assert result.status == "cleaned"
        assert result.original_char_count > result.cleaned_char_count
        assert result.document is not None
        assert result.document.id == "circular_001"
        assert result.document.metadata["authority"] == "RBI"
        assert result.document.metadata["circular_no"] == "2024/01"
        assert result.document.text == "Section 1. Scope of Directive."

    def test_clean_corpus_batch(self) -> None:
        docs = [
            Document(id="doc1", text="Clean document text without noise."),
            Document(id="doc2", text="Noisy   document  text.\r\nPage 1 of 2"),
            Document(id="doc3", text="Third  document   sample."),
        ]
        cleaned_docs, summary = clean_corpus(docs)
        assert summary.total_documents == 3
        assert summary.processed == 3
        assert summary.failed == 0
        assert len(cleaned_docs) == 3
        assert summary.total_original_chars >= summary.total_cleaned_chars

    def test_clean_corpus_directory_and_source_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_in_dir, tempfile.TemporaryDirectory() as tmp_out_dir:
            in_path = Path(tmp_in_dir)
            out_path = Path(tmp_out_dir)

            file1 = in_path / "circular_a.txt"
            raw_content = "Raw   content   line.\r\nPage 1 of 1"
            file1.write_text(raw_content, encoding="utf-8")

            summary = clean_corpus_directory(
                input_dir=in_path,
                output_dir=out_path,
            )

            assert summary.total_documents == 1
            assert summary.processed == 1

            # Verify cleaned file was created in output directory
            out_file = out_path / "circular_a.txt"
            assert out_file.exists()
            assert out_file.read_text(encoding="utf-8") == "Raw content line."

            # Verify RAW SOURCE FILE was NOT overwritten or modified!
            assert file1.read_bytes() == raw_content.encode("utf-8")
