# Data Directory Structure

This directory stores regulatory circulars, compliance guidelines, and processed artifacts for ChronoLex.

## Directories

- `raw/`: Unprocessed regulatory documents (e.g., PDF circulars, regulatory advisories, internal bank compliance policies).
- `processed/`: Cleaned text corpora, extraction metadata, and generated chunk representations prior to vector indexing.

## Governance & Hygiene

- Raw binary PDFs and large datasets are excluded from Git via `.gitignore`.
- Only test fixtures or reference samples should ever be checked in if necessary.
- Documents placed in `raw/` should preserve their original naming and provenance metadata (issuing authority, date, reference circular number).
