"""Reusable, layout-aware text cleaning and normalization utilities for ChronoLex.

Designed for banking regulatory circulars, compliance directives, and statutory texts.
Performs cleaning in a deliberate, conservative multi-stage sequence:
1. Unicode and line ending normalization (NFKC, CRLF -> LF, NBSP, zero-width chars, safe mojibake repair).
2. Page-number boilerplate removal (Page X of Y, Page X, - Page X -, line-oriented without corrupting body text).
3. Repeated header & footer removal (frequency-based detection across pages/sections + configurable boilerplate patterns).
4. Whitespace normalization (collapsing extra spaces/tabs, trailing space stripping, max 2 consecutive newlines, trimming).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence

# Common UTF-8 misinterpretations (decoded as Windows-1252 or ISO-8859-1)
# Safe, targeted repairs only. Never blindly re-encode the entire text.
KNOWN_MOJIBAKE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("â€™", "’"),   # Right single quote / apostrophe
    ("â€˜", "‘"),   # Left single quote
    ("â€œ", "“"),   # Left double quote
    ("â€\x9d", "”"), # Right double quote (Windows-1252 0x9D)
    ("â€", "”"),   # Right double quote (alternate decode)
    ("â€“", "–"),   # En dash
    ("â€”", "—"),   # Em dash
    ("â€¦", "…"),   # Ellipsis
    ("Â\xa0", " "), # Non-breaking space mojibake
    ("Â ", " "),    # Non-breaking space mojibake
    ("Ã©", "é"),    # Acute accent e
    ("Ã¨", "è"),    # Grave accent e
    ("Ã±", "ñ"),    # Tilde n
    ("Â§", "§"),    # Section sign
    ("Â©", "©"),    # Copyright sign
    ("Â®", "®"),    # Registered sign
)

# Invisible and zero-width characters to strip
ZERO_WIDTH_CHARS: tuple[str, ...] = (
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\ufeff",  # Byte order mark (BOM)
    "\u2060",  # Word joiner
)

# Regex for standalone page-number lines
# Matches lines like:
# "Page 1", "Page 3 of 12", "- Page 4 of 20 -", "— Page 5 —", "[Page 2]", "Page 3 / 10",
# "p. 1", "pg. 5", "- 12 -", "[12]"
PAGE_NUMBER_LINE_REGEX = re.compile(
    r"^[ \t]*"
    r"(?:[-—–~_\[(][ \t]*)?"
    r"(?:"
    r"(?:page|pg\.?|p\.)[ \t]*\d+(?:[ \t]*(?:of|/)[ \t]*\d+)?"
    r"|\d+[ \t]*(?:of|/)[ \t]*\d+"
    r"|(?:[-—–~_\[(])[ \t]*\d+[ \t]*(?:[-—–~_\])])"
    r")"
    r"(?:[ \t]*[-—–~_\])])?"
    r"[ \t]*$",
    re.IGNORECASE,
)


def repair_mojibake(text: str) -> str:
    """Safely repairs known, high-confidence UTF-8 mojibake sequences.

    Does NOT blindly re-encode the entire string to avoid data loss on mixed encodings.
    """
    for bad, good in KNOWN_MOJIBAKE_REPLACEMENTS:
        if bad in text:
            text = text.replace(bad, good)
    return text


def normalize_unicode_and_newlines(
    text: str,
    repair_encoding_artifacts: bool = True,
) -> str:
    """Normalizes Unicode characters and standardizes line endings.

    Steps:
    1. Validates string input type.
    2. Normalizes line endings (\\r\\n and \\r to \\n).
    3. Repairs targeted mojibake sequences if enabled.
    4. Applies Unicode NFKC normalization.
    5. Replaces non-breaking and zero-width spaces with standard spaces or removes them.

    Args:
        text: Input raw text.
        repair_encoding_artifacts: Whether to apply targeted mojibake repairs.

    Returns:
        Normalized text with uniform \\n line endings.

    Raises:
        TypeError: If text is not an instance of str.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    if not text:
        return ""

    # Normalize Windows and legacy Mac line endings to standard Unix newline
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Safe mojibake repair before NFKC
    if repair_encoding_artifacts:
        text = repair_mojibake(text)

    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # Replace non-breaking spaces (NBSP and narrow NBSP) with standard ASCII space
    text = text.replace("\u00a0", " ").replace("\u202f", " ")

    # Strip zero-width characters and BOM
    for zw in ZERO_WIDTH_CHARS:
        if zw in text:
            text = text.replace(zw, "")

    return text


def remove_page_numbers(text: str) -> str:
    """Removes standalone page-number boilerplate lines.

    Preserves occurrences of page numbers or 'page' references inside running text,
    such as 'refer to page 3 of 12 for definitions' or 'Section 4: Page limits'.

    Args:
        text: Input text.

    Returns:
        Text with standalone page-number lines removed.
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        if PAGE_NUMBER_LINE_REGEX.match(line):
            # Skip standalone page number line
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def detect_repeated_headers_footers(
    text: str,
    min_repetitions: int = 2,
    header_footer_zone_lines: int = 3,
) -> set[str]:
    """Detects recurring header and footer candidates across pages or sections.

    A line is classified as a header/footer candidate ONLY IF:
    1. The document contains page markers (e.g., form feed '\\x0c' or '--- Page'), AND
    2. The exact line appears in the top or bottom N lines of multiple pages.

    This prevents false positives on repeated section titles, bullet headings,
    or regulatory clauses that legitimately occur throughout a document.

    Args:
        text: Input document text.
        min_repetitions: Minimum number of pages a candidate line must appear on.
        header_footer_zone_lines: Number of lines at top and bottom of each page to inspect.

    Returns:
        Set of detected boilerplate header/footer line contents.
    """
    # Detect pages via form feed character '\x0c' or explicit page break markers
    pages = re.split(r"\x0c|(?:\n[ \t]*[-=]{3,}[ \t]*(?:Page Break|Page \d+)[ \t]*[-=]{3,}\n)", text)
    if len(pages) < min_repetitions:
        return set()

    line_page_counts: dict[str, set[int]] = {}

    for page_idx, page in enumerate(pages):
        raw_lines = [line.strip() for line in page.split("\n") if line.strip()]
        if not raw_lines:
            continue

        # Look at the top and bottom zone of the page
        top_zone = raw_lines[:header_footer_zone_lines]
        bottom_zone = raw_lines[-header_footer_zone_lines:] if len(raw_lines) > header_footer_zone_lines else []
        candidates = set(top_zone + bottom_zone)

        for line in candidates:
            # Skip very short lines or digit-only lines (handled by page number removal)
            if len(line) < 4:
                continue
            line_page_counts.setdefault(line, set()).add(page_idx)

    # Return lines that recur in >= min_repetitions pages
    repeated = {
        line for line, page_set in line_page_counts.items()
        if len(page_set) >= min_repetitions
    }
    return repeated


def remove_repeated_boilerplate(
    text: str,
    known_boilerplate: Sequence[str] | None = None,
    min_repetitions: int = 2,
) -> str:
    """Removes repeated headers, footers, and configured boilerplate patterns.

    Conservative rule:
    - Automatically removes lines matching `known_boilerplate`.
    - If page boundaries are present, detects lines repeated in header/footer zones across pages.
    - If NO page boundaries are present, does NOT remove arbitrary repeating lines,
      protecting legitimate regulatory repetition (e.g. repeated section prefixes).

    Args:
        text: Input text.
        known_boilerplate: Optional list of regex patterns or exact string phrases to remove.
        min_repetitions: Minimum page repetitions for auto-detected headers/footers.

    Returns:
        Text with boilerplate removed.
    """
    if not text:
        return ""

    detected_repeats = detect_repeated_headers_footers(text, min_repetitions=min_repetitions)

    # Compile known boilerplate patterns
    known_patterns: list[re.Pattern[str]] = []
    if known_boilerplate:
        for item in known_boilerplate:
            if not item.strip():
                continue
            # If item contains regex special chars, compile directly, else match full line or phrase
            try:
                known_patterns.append(re.compile(item, re.IGNORECASE))
            except re.error:
                known_patterns.append(re.compile(re.escape(item), re.IGNORECASE))

    lines = text.split("\n")
    filtered_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Check detected recurring header/footer lines
        if stripped in detected_repeats:
            continue

        # Check against known boilerplate patterns (matching entire line or clear standalone banners)
        matched_known = False
        for pattern in known_patterns:
            if pattern.search(stripped):
                # If pattern matches the entire stripped line or is a standalone banner
                if pattern.fullmatch(stripped) or pattern.search(line):
                    matched_known = True
                    break

        if matched_known:
            continue

        filtered_lines.append(line)

    result = "\n".join(filtered_lines)
    # Strip form feed markers if they were used for page boundary detection
    result = result.replace("\x0c", "\n")
    return result


def normalize_whitespace(text: str) -> str:
    """Normalizes whitespace while preserving document structure.

    Operations:
    1. Collapses consecutive horizontal spaces and tabs into a single space (per line).
    2. Strips trailing whitespace from each line.
    3. Collapses three or more consecutive newlines to at most two (preserving paragraph boundaries).
    4. Trims leading and trailing whitespace from the document.

    Preserves:
    - Meaningful paragraph boundaries (\\n\\n).
    - Headings and list structures (bullets, numbers).
    - Regulatory section identifiers, dates, and punctuation.
    - Table rows separated by newlines.

    Args:
        text: Input text.

    Returns:
        Whitespace-normalized text.
    """
    if not text:
        return ""

    lines = text.split("\n")
    normalized_lines: list[str] = []

    for line in lines:
        # Collapse multiple horizontal spaces and tabs to a single space
        collapsed = re.sub(r"[ \t]+", " ", line)
        # Strip trailing whitespace from the line
        trimmed = collapsed.rstrip()
        normalized_lines.append(trimmed)

    reconstructed = "\n".join(normalized_lines)

    # Collapse 3 or more consecutive newlines into at most 2 (double newline = paragraph break)
    reconstructed = re.sub(r"\n{3,}", "\n\n", reconstructed)

    # Trim leading and trailing whitespace of the overall document
    return reconstructed.strip()


def clean_text(
    text: str,
    known_boilerplate: Sequence[str] | None = None,
    repair_encoding_artifacts: bool = True,
    remove_pages: bool = True,
    remove_boilerplate: bool = True,
    normalize_spaces: bool = True,
) -> str:
    """Comprehensive, reusable cleaning pipeline for regulatory and compliance text.

    Executes all cleaning stages in deliberate order:
    1. Unicode and line ending normalization (NFKC, CRLF -> LF, NBSP, safe mojibake repair).
    2. Standalone page-number boilerplate removal.
    3. Repeated header, footer, and configurable boilerplate removal.
    4. Structural whitespace normalization.

    Args:
        text: Raw extracted document text.
        known_boilerplate: Optional sequence of known boilerplate strings or patterns to strip.
        repair_encoding_artifacts: Whether to repair common UTF-8 mojibake (default True).
        remove_pages: Whether to remove standalone page-number lines (default True).
        remove_boilerplate: Whether to detect and remove recurring headers/footers (default True).
        normalize_spaces: Whether to normalize spaces, tabs, and newlines (default True).

    Returns:
        Cleaned, normalized text ready for intelligent chunking and embedding.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    if not text:
        return ""

    # Stage 1: Unicode NFKC and line endings
    cleaned = normalize_unicode_and_newlines(
        text,
        repair_encoding_artifacts=repair_encoding_artifacts,
    )

    # Stage 2: Page numbers
    if remove_pages:
        cleaned = remove_page_numbers(cleaned)

    # Stage 3: Repeated headers and footers
    if remove_boilerplate:
        cleaned = remove_repeated_boilerplate(
            cleaned,
            known_boilerplate=known_boilerplate,
        )

    # Stage 4: Whitespace normalization
    if normalize_spaces:
        cleaned = normalize_whitespace(cleaned)

    return cleaned
