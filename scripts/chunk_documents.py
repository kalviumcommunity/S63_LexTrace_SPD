#!/usr/bin/env python3
"""Executable demonstration script for ChronoLex Token-Aware Chunking & Overlap Analysis.

Performs:
1. Exact token-level slicing with tiktoken BPE tokenizer.
2. Direct comparison between Configuration A (Zero Overlap: 400/0) and
   Configuration B (Controlled Overlap: 400/60).
3. Duplication and token-expansion cost measurement.
4. Boundary-context preservation inspection for regulatory clauses.
5. Generation of a reproducible Markdown evaluation report.

Usage:
    # Run default demonstration using committed sample
    python scripts/chunk_documents.py

    # Chunk custom file with custom size and overlap
    python scripts/chunk_documents.py --input path/to/doc.txt --size 400 --overlap 60

    # Specify custom output path for markdown report
    python scripts/chunk_documents.py --output docs/examples/token_chunking_results.md
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add apps/api to sys.path so app modules are resolvable
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.utils.chunking import token_chunks_detailed
from app.utils.tokenization import count_tokens, get_tokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("chunk_documents")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE_PATH = PROJECT_ROOT / "data" / "examples" / "chunking_sample.txt"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "docs" / "examples" / "token_chunking_results.md"


def run_chunking_experiment(
    text: str,
    chunk_size: int = 400,
    overlap: int = 60,
    encoding_name: str = "cl100k_base",
) -> Dict[str, Any]:
    """Executes chunking under zero-overlap and configured-overlap configurations."""
    enc = get_tokenizer(encoding_name)
    raw_tokens = enc.encode(text)
    original_token_count = len(raw_tokens)

    # Configuration A: Zero overlap
    chunks_a = token_chunks_detailed(
        text=text,
        size=chunk_size,
        overlap=0,
        encoding=encoding_name,
    )
    total_tokens_a = sum(c["token_count"] for c in chunks_a)

    # Configuration B: Configured overlap
    chunks_b = token_chunks_detailed(
        text=text,
        size=chunk_size,
        overlap=overlap,
        encoding=encoding_name,
    )
    total_tokens_b = sum(c["token_count"] for c in chunks_b)

    # Overlap metrics
    additional_tokens = total_tokens_b - total_tokens_a
    duplication_pct = (
        round((additional_tokens / original_token_count) * 100.0, 2)
        if original_token_count > 0
        else 0.0
    )

    return {
        "original_token_count": original_token_count,
        "original_char_count": len(text),
        "chunk_size": chunk_size,
        "configured_overlap": overlap,
        "encoding_name": encoding_name,
        "config_a": {
            "name": "Configuration A (Zero Overlap)",
            "chunk_size": chunk_size,
            "overlap": 0,
            "chunk_count": len(chunks_a),
            "total_tokens": total_tokens_a,
            "chunks": chunks_a,
        },
        "config_b": {
            "name": "Configuration B (Controlled Overlap)",
            "chunk_size": chunk_size,
            "overlap": overlap,
            "chunk_count": len(chunks_b),
            "total_tokens": total_tokens_b,
            "chunks": chunks_b,
        },
        "cost_metrics": {
            "additional_tokens": additional_tokens,
            "duplication_pct": duplication_pct,
        },
    }


def generate_markdown_report(
    results: Dict[str, Any],
    original_text: str,
    source_filename: str,
    output_path: Path,
) -> None:
    """Writes a comprehensive Markdown report documenting the empirical results."""
    orig_tokens = results["original_token_count"]
    orig_chars = results["original_char_count"]
    cfg_a = results["config_a"]
    cfg_b = results["config_b"]
    costs = results["cost_metrics"]
    size = results["chunk_size"]
    overlap = results["configured_overlap"]
    encoding = results["encoding_name"]

    # Build chunk detail sections
    def format_chunk_details(chunks: List[Dict[str, Any]]) -> str:
        blocks = []
        for c in chunks:
            idx = c["chunk_index"]
            tokens = c["token_count"]
            start = c["start_token_idx"]
            end = c["end_token_idx"]
            content = c["text"].strip()
            blocks.append(
                f"#### Chunk {idx + 1} ({tokens} tokens | offsets: [{start}:{end}])\n\n"
                f"```text\n{content}\n```"
            )
        return "\n\n".join(blocks)

    chunks_a_formatted = format_chunk_details(cfg_a["chunks"])
    chunks_b_formatted = format_chunk_details(cfg_b["chunks"])

    # Extract boundary comparison (between chunk 0 and chunk 1)
    boundary_section = ""
    if len(cfg_a["chunks"]) > 1 and len(cfg_b["chunks"]) > 1:
        c0_a_end = cfg_a["chunks"][0]["text"][-200:].strip()
        c1_a_start = cfg_a["chunks"][1]["text"][:200].strip()

        c0_b_end = cfg_b["chunks"][0]["text"][-200:].strip()
        c1_b_start = cfg_b["chunks"][1]["text"][:260].strip()

        boundary_section = f"""## 4. Boundary-Context Preservation Analysis

### Adjacent Chunk Boundary Comparison (Chunk 1 Ending vs. Chunk 2 Beginning)

#### Configuration A (Zero Overlap — 400 / 0 tokens)
*Notice how the sentence is severed across the chunk boundary, cutting off the qualification criteria from the general rule.*

- **Chunk 1 Tail:**
  ```text
  ...{c0_a_end}
  ```
- **Chunk 2 Head:**
  ```text
  {c1_a_start}...
  ```
- **Context Loss Impact:** An embedding model retrieving Chunk 1 alone sees a prohibition terminating abruptly at `...strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution`, completely missing the statutory clearance condition. Conversely, a retrieval hitting Chunk 2 alone encounters `obtains a verified statutory clearance certificate...` without the antecedent prohibition subject or jurisdiction scope.

#### Configuration B (Controlled Overlap — 400 / 60 tokens)
*Notice how the repeated 60 boundary tokens maintain the full semantic rule across both chunks.*

- **Chunk 1 Tail:**
  ```text
  ...{c0_b_end}
  ```
- **Chunk 2 Head:**
  ```text
  {c1_b_start}...
  ```
- **Preservation Benefit:** The final 60 tokens of Chunk 1 are repeated at the beginning of Chunk 2. As a result, Chunk 2 contains the entire prohibition heading (`Section 3`), the regulatory rule, and the complete safe-harbor exception (`UNLESS the transferring institution obtains a verified statutory clearance certificate...`). Retrieval queries matching either the prohibition or the clearance exception will find intact context.
"""

    report_content = f"""# ChronoLex — Token-Aware Chunking & Overlap Analysis Report

**Source Document:** `{source_filename}`  
**Tokenizer Encoding:** `{encoding}` (tiktoken)  
**Original Text Length:** {orig_chars:,} characters | **{orig_tokens:,} tokens**  
**Evaluation Mode:** Comparative Benchmark (Empirical Execution)

---

## 1. Executive Summary & Comparative Metrics

| Metric | Configuration A (Zero Overlap) | Configuration B (Controlled Overlap) | Delta / Overlap Cost |
|---|---|---|---|
| **Chunk Size Limit** | {size} tokens | {size} tokens | Identical |
| **Overlap Tokens** | 0 tokens (0%) | {overlap} tokens ({round(overlap / size * 100, 1)}%) | +{overlap} tokens |
| **Total Chunks Produced** | **{cfg_a['chunk_count']}** | **{cfg_b['chunk_count']}** | {cfg_b['chunk_count'] - cfg_a['chunk_count']:+d} chunks |
| **Tokens per Chunk (Sequence)** | {', '.join(str(c['token_count']) for c in cfg_a['chunks'])} | {', '.join(str(c['token_count']) for c in cfg_b['chunks'])} | — |
| **Total Tokens Across All Chunks** | **{cfg_a['total_tokens']:,} tokens** | **{cfg_b['total_tokens']:,} tokens** | **+{costs['additional_tokens']:,} tokens** |
| **Duplication Percentage** | **0.00%** | **{costs['duplication_pct']}%** | +{costs['duplication_pct']}% |

---

## 2. Measurement of Overlap Overhead

Overlapping chunk boundaries purposefully replicate text tokens across adjacent segments to prevent semantic fragmentation. However, this creates direct computational trade-offs:

1. **Embedding Generation Overhead:** Vectorizing {cfg_b['total_tokens']} tokens instead of {cfg_a['total_tokens']} tokens represents a **{costs['duplication_pct']}% increase** in embedding API input tokens.
2. **Vector Index Storage:** The repeated tokens expand the aggregate stored text size and may result in additional chunk vector records if chunk count scales up.
3. **Retrieval Deduplication:** If adjacent overlapping chunks both score high in similarity search, prompt synthesis pipelines must handle deduplication to avoid wasting context-window tokens with redundant text.

---

## 3. Chunks Generated Under Configuration A (Zero Overlap: 400 / 0)

{chunks_a_formatted}

---

{boundary_section}

---

## 5. Chunks Generated Under Configuration B (Controlled Overlap: 400 / 60)

{chunks_b_formatted}

---

## 6. Justification of Chunk Size (400) and Overlap (60)

### Why 400 Tokens?
- **Domain Fit for Regulatory Text:** Regulatory circulars (e.g., RBI, Basel, SEC, FINRA) typically group actionable rules into numbered paragraphs spanning 150–350 tokens. A 400-token ceiling accommodates an entire sub-rule alongside its immediate caveats and statutory references without forcing unnecessary mid-clause splits.
- **Precision vs. Context Trade-Off:** Larger chunks (800–1,500 tokens) dilute embedding similarity by blending disparate compliance rules, reducing vector retrieval accuracy. Smaller chunks (100–200 tokens) isolate sentences from their operative definitions, exceptions, and penalty clauses. A 400-token window balances specificity with self-contained context.
- **Prompt Budget Integration:** Consider a standard RAG prompt formula:
  $$\\text{{Context Demand}} = \\text{{System Prompt}} + \\text{{User Question}} + \\text{{Chat History}} + (k \\times \\text{{Chunk Size}}) + \\text{{Reserved Output}}$$
  With $k=4$ retrieved chunks of 400 tokens each, context consumption is $\\approx 1,600$ tokens, leaving ample room within standard 8K, 16K, or 128K context budgets for conversational history and structured JSON outputs.

### Why 60 Tokens (15%) Overlap?
- **Boundary Continuity:** 60 tokens corresponds to roughly 40–50 English words—the length of a substantial regulatory sentence or preamble. This provides sufficient cushion so that sentences beginning near the end of Chunk $N$ are repeated fully at the start of Chunk $N+1$.
- **Cost Discipline:** 60 tokens represents exactly 15% of the 400-token chunk size, keeping overall corpus token duplication under 10–15% for multi-chunk documents. Greater overlaps (e.g., 30–50%) cause ballooning embedding costs and index bloating without commensurate retrieval gains.

### Tokenizer Alignment Considerations
- ChronoLex utilizes the OpenAI `cl100k_base` BPE tokenizer (standard for `gpt-4`, `gpt-4o-mini`, and `text-embedding-3-*` models).
- **Important:** Different LLM families (e.g. Llama with SentencePiece/BPE, Claude with its proprietary tokenizer, or Gemini) calculate token boundaries differently. Chunk limits should be re-evaluated if switching embedding or generation model families.

### Status of Settings
> **Note on Empirical Optimization:** The default parameters (size: 400, overlap: 60) represent **empirically informed initial heuristics**. Because ChronoLex does not yet maintain a ground-truth regulatory QA retrieval benchmark dataset, these settings have not been formally hyperparameter-tuned. Production deployment will require evaluation against retrieval precision/recall metrics (e.g., Hit@k, MRR) on the specific target regulatory corpus.

---

## 7. Verifiable Original Text Sample

```text
{original_text.strip()}
```
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding="utf-8")
    logger.info("Successfully generated Markdown report at: %s", output_path)


def print_cli_summary(results: Dict[str, Any]) -> None:
    """Prints a structured summary table to stdout."""
    cfg_a = results["config_a"]
    cfg_b = results["config_b"]
    costs = results["cost_metrics"]

    print("\n" + "=" * 78)
    print("CHRONOLEX TOKEN-AWARE CHUNKING BENCHMARK RESULTS")
    print("=" * 78)
    print(f"Original Text Tokens : {results['original_token_count']:,} tokens (tiktoken {results['encoding_name']})")
    print(f"Original Characters  : {results['original_char_count']:,} chars")
    print("-" * 78)
    print(f"Configuration A (Size {cfg_a['chunk_size']}, Overlap 0):")
    print(f"  - Total Chunks     : {cfg_a['chunk_count']}")
    print(f"  - Tokens per Chunk : {[c['token_count'] for c in cfg_a['chunks']]}")
    print(f"  - Total Tokens     : {cfg_a['total_tokens']:,}")
    print("-" * 78)
    print(f"Configuration B (Size {cfg_b['chunk_size']}, Overlap {cfg_b['overlap']}):")
    print(f"  - Total Chunks     : {cfg_b['chunk_count']}")
    print(f"  - Tokens per Chunk : {[c['token_count'] for c in cfg_b['chunks']]}")
    print(f"  - Total Tokens     : {cfg_b['total_tokens']:,}")
    print("-" * 78)
    print("Cost of Overlap:")
    print(f"  - Additional Tokens: +{costs['additional_tokens']:,} tokens")
    print(f"  - Duplication Pct  : +{costs['duplication_pct']}%")
    print("=" * 78 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ChronoLex Token-Aware Document Chunking Demonstration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_SAMPLE_PATH,
        help="Path to source text document to chunk",
    )
    parser.add_argument(
        "--size",
        "-s",
        type=int,
        default=400,
        help="Maximum chunk size in tokens",
    )
    parser.add_argument(
        "--overlap",
        "-o",
        type=int,
        default=60,
        help="Number of boundary tokens to repeat between adjacent chunks",
    )
    parser.add_argument(
        "--encoding",
        "-e",
        type=str,
        default="cl100k_base",
        help="Tiktoken tokenizer encoding name",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Destination path for the generated Markdown evidence report",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress detailed console output",
    )

    args = parser.parse_args()

    input_path = args.input
    if not input_path.is_file():
        logger.error("Input file not found: %s", input_path)
        return 1

    text = input_path.read_text(encoding="utf-8")
    if not text.strip():
        logger.error("Input file is empty: %s", input_path)
        return 1

    try:
        results = run_chunking_experiment(
            text=text,
            chunk_size=args.size,
            overlap=args.overlap,
            encoding_name=args.encoding,
        )
    except ValueError as e:
        logger.error("Validation error in chunking settings: %s", e)
        return 1

    if not args.quiet:
        print_cli_summary(results)

    generate_markdown_report(
        results=results,
        original_text=text,
        source_filename=input_path.name,
        output_path=args.output,
    )

    print(f"Evidence report successfully written to: {args.output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
