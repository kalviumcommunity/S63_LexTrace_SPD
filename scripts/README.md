# ChronoLex Automation & Helper Scripts

This directory is designated for data processing, ingestion helpers, and developer utilities.

## Active Scripts

- `scripts/clean_documents.py`: CLI tool for cleaning raw regulatory text documents and directories, stripping boilerplate/page numbers, repairing encoding artifacts, preserving metadata, and generating before/after evidence reports.
- `scripts/demo_structured.py`: Demonstration script for structured LLM JSON outputs, Pydantic schema validation, and bounded retry recovery.
- `scripts/demo_prompts.py`: Experiments comparing vague vs. specific system/user prompts and grounding guardrails.
- `scripts/demo_llm.py`: Baseline OpenAI-compatible LLM connectivity and token usage verification.
- `scripts/token_cost_demo.py`: Token counting and cost modeling across models and context budgets.

## Planned Scripts (Upcoming Milestones)

- `scripts/ingest_corpus.py`: Ingests and processes multi-page PDF documents from `data/raw/` into layout-aware parsed text.
- `scripts/index_vector_db.py`: Generates dense embeddings for chunked data and indexes them into ChromaDB.
- `scripts/eval_retrieval.py`: Benchmark suite for retrieval accuracy, Top-K precision, and time-aware filtering performance.
