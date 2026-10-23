# ChronoLex — Token-Aware Chunking & Overlap Analysis Report

**Source Document:** `chunking_sample.txt`  
**Tokenizer Encoding:** `cl100k_base` (tiktoken)  
**Original Text Length:** 3,200 characters | **689 tokens**  
**Evaluation Mode:** Comparative Benchmark (Empirical Execution)

---

## 1. Executive Summary & Comparative Metrics

| Metric | Configuration A (Zero Overlap) | Configuration B (Controlled Overlap) | Delta / Overlap Cost |
|---|---|---|---|
| **Chunk Size Limit** | 400 tokens | 400 tokens | Identical |
| **Overlap Tokens** | 0 tokens (0%) | 60 tokens (15.0%) | +60 tokens |
| **Total Chunks Produced** | **2** | **2** | +0 chunks |
| **Tokens per Chunk (Sequence)** | 400, 289 | 400, 349 | — |
| **Total Tokens Across All Chunks** | **689 tokens** | **749 tokens** | **+60 tokens** |
| **Duplication Percentage** | **0.00%** | **8.71%** | +8.71% |

---

## 2. Measurement of Overlap Overhead

Overlapping chunk boundaries purposefully replicate text tokens across adjacent segments to prevent semantic fragmentation. However, this creates direct computational trade-offs:

1. **Embedding Generation Overhead:** Vectorizing 749 tokens instead of 689 tokens represents a **8.71% increase** in embedding API input tokens.
2. **Vector Index Storage:** The repeated tokens expand the aggregate stored text size and may result in additional chunk vector records if chunk count scales up.
3. **Retrieval Deduplication:** If adjacent overlapping chunks both score high in similarity search, prompt synthesis pipelines must handle deduplication to avoid wasting context-window tokens with redundant text.

---

## 3. Chunks Generated Under Configuration A (Zero Overlap: 400 / 0)

#### Chunk 1 (400 tokens | offsets: [0:400])

```text
RBI/2024-25/108
NOTIFICATION: MASTER DIRECTION – WIRE TRANSFER MONITORING AND CUSTOMER DUE DILIGENCE
Effective Date: April 1, 2024
Review Date: 2026-03-31
Issuing Authority: Reserve Bank of India, Department of Banking Regulation

Section 1. Legislative Authority & Scope
In exercise of the powers conferred by Section 35A of the Banking Regulation Act, 1949, the Reserve Bank of India hereby issues these mandatory directives to all Regulated Entities (REs), including commercial banks, cooperative societies, payment aggregators, and authorized non-banking institutions operating payment corridors.

The RE's audit team shall review compliance with these guidelines on a quarterly basis. Every bank's board of directors must record the compliance officer's annual declaration of conformance and verify that automated transaction screening algorithms are audited by a CERT-In empanelled auditor.

Section 2. Mandatory Thresholds for Cross-Border Transactions

2.1. Customer Due Diligence (CDD) Requirements:
1. All cross-border wire transfers exceeding $10,000 USD (or foreign currency equivalent) require complete originator and beneficiary verification prior to fund execution.
2. Cash transactions exceeding 50,000 INR require verification of Permanent Account Number (PAN) or Form 60 declaration.
3. Wire transfers initiated for high-risk accounts shall be subject to mandatory Enhanced Due Diligence (EDD) under Rule 14.2(c).
4. Intermediary institutions involved in multi-hop correspondent payment routing must retain all technical wire messaging headers (SWIFT MT103 / ISO 20022 message structures) intact throughout transmission.

Section 3. Sanctions Screening and Safe-Harbor Clearance Protocols

3.1. General Prohibition and Safe-Harbor Exemption:
Regulated entities maintaining correspondent banking corridors are strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution
```

#### Chunk 2 (289 tokens | offsets: [400:689])

```text
obtains a verified statutory clearance certificate issued by the Financial Intelligence Unit (FIU-IND) within twenty-four hours of transaction initiation.

Section 4. Capital Adequacy and Risk-Weighted Reserve Requirements

Regulated entities maintaining cross-border remittance facilities must preserve supplementary tier-1 liquid buffers against settlement latency and currency variance.

| Capital Tier | Minimum CET1 Ratio | Capital Conservation Buffer | Countercyclical Buffer |
| Tier 1 Primary | 5.5% | 2.5% | 0.0% - 2.5% |
| Tier 2 Subordinated | 2.0% | N/A | N/A |
| Total Regulatory Capital | 9.0% | 2.5% | Dynamic Countercyclical |

Section 5. Record Retention, Reporting Protocols, and Penal Sanctions

5.1. General Rule:
All records of transactions, account-opening dossiers, identity credentials, and beneficial ownership declarations shall be preserved for a minimum period of ten (10) years from the transaction date in tamper-evident electronic archives.

5.2. Statutory Penalties:
Failure to adhere to these directions will attract statutory penalties under Section 47A(1)(c) of the Banking Regulation Act, 1949, including pecuniary fines up to 10,000,000 INR and potential suspension of authorized dealer category banking licenses.
```

---

## 4. Boundary-Context Preservation Analysis

### Adjacent Chunk Boundary Comparison (Chunk 1 Ending vs. Chunk 2 Beginning)

#### Configuration A (Zero Overlap — 400 / 0 tokens)
*Notice how the sentence is severed across the chunk boundary, cutting off the qualification criteria from the general rule.*

- **Chunk 1 Tail:**
  ```text
  ...Exemption:
Regulated entities maintaining correspondent banking corridors are strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution
  ```
- **Chunk 2 Head:**
  ```text
  obtains a verified statutory clearance certificate issued by the Financial Intelligence Unit (FIU-IND) within twenty-four hours of transaction initiation.

Section 4. Capital Adequacy and Risk-Weight...
  ```
- **Context Loss Impact:** An embedding model retrieving Chunk 1 alone sees a prohibition terminating abruptly at `...strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution`, completely missing the statutory clearance condition. Conversely, a retrieval hitting Chunk 2 alone encounters `obtains a verified statutory clearance certificate...` without the antecedent prohibition subject or jurisdiction scope.

#### Configuration B (Controlled Overlap — 400 / 60 tokens)
*Notice how the repeated 60 boundary tokens maintain the full semantic rule across both chunks.*

- **Chunk 1 Tail:**
  ```text
  ...Exemption:
Regulated entities maintaining correspondent banking corridors are strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution
  ```
- **Chunk 2 Head:**
  ```text
  ) intact throughout transmission.

Section 3. Sanctions Screening and Safe-Harbor Clearance Protocols

3.1. General Prohibition and Safe-Harbor Exemption:
Regulated entities maintaining correspondent banking corridors are strictly prohibited from executing wir...
  ```
- **Preservation Benefit:** The final 60 tokens of Chunk 1 are repeated at the beginning of Chunk 2. As a result, Chunk 2 contains the entire prohibition heading (`Section 3`), the regulatory rule, and the complete safe-harbor exception (`UNLESS the transferring institution obtains a verified statutory clearance certificate...`). Retrieval queries matching either the prohibition or the clearance exception will find intact context.


---

## 5. Chunks Generated Under Configuration B (Controlled Overlap: 400 / 60)

#### Chunk 1 (400 tokens | offsets: [0:400])

```text
RBI/2024-25/108
NOTIFICATION: MASTER DIRECTION – WIRE TRANSFER MONITORING AND CUSTOMER DUE DILIGENCE
Effective Date: April 1, 2024
Review Date: 2026-03-31
Issuing Authority: Reserve Bank of India, Department of Banking Regulation

Section 1. Legislative Authority & Scope
In exercise of the powers conferred by Section 35A of the Banking Regulation Act, 1949, the Reserve Bank of India hereby issues these mandatory directives to all Regulated Entities (REs), including commercial banks, cooperative societies, payment aggregators, and authorized non-banking institutions operating payment corridors.

The RE's audit team shall review compliance with these guidelines on a quarterly basis. Every bank's board of directors must record the compliance officer's annual declaration of conformance and verify that automated transaction screening algorithms are audited by a CERT-In empanelled auditor.

Section 2. Mandatory Thresholds for Cross-Border Transactions

2.1. Customer Due Diligence (CDD) Requirements:
1. All cross-border wire transfers exceeding $10,000 USD (or foreign currency equivalent) require complete originator and beneficiary verification prior to fund execution.
2. Cash transactions exceeding 50,000 INR require verification of Permanent Account Number (PAN) or Form 60 declaration.
3. Wire transfers initiated for high-risk accounts shall be subject to mandatory Enhanced Due Diligence (EDD) under Rule 14.2(c).
4. Intermediary institutions involved in multi-hop correspondent payment routing must retain all technical wire messaging headers (SWIFT MT103 / ISO 20022 message structures) intact throughout transmission.

Section 3. Sanctions Screening and Safe-Harbor Clearance Protocols

3.1. General Prohibition and Safe-Harbor Exemption:
Regulated entities maintaining correspondent banking corridors are strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution
```

#### Chunk 2 (349 tokens | offsets: [340:689])

```text
) intact throughout transmission.

Section 3. Sanctions Screening and Safe-Harbor Clearance Protocols

3.1. General Prohibition and Safe-Harbor Exemption:
Regulated entities maintaining correspondent banking corridors are strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution obtains a verified statutory clearance certificate issued by the Financial Intelligence Unit (FIU-IND) within twenty-four hours of transaction initiation.

Section 4. Capital Adequacy and Risk-Weighted Reserve Requirements

Regulated entities maintaining cross-border remittance facilities must preserve supplementary tier-1 liquid buffers against settlement latency and currency variance.

| Capital Tier | Minimum CET1 Ratio | Capital Conservation Buffer | Countercyclical Buffer |
| Tier 1 Primary | 5.5% | 2.5% | 0.0% - 2.5% |
| Tier 2 Subordinated | 2.0% | N/A | N/A |
| Total Regulatory Capital | 9.0% | 2.5% | Dynamic Countercyclical |

Section 5. Record Retention, Reporting Protocols, and Penal Sanctions

5.1. General Rule:
All records of transactions, account-opening dossiers, identity credentials, and beneficial ownership declarations shall be preserved for a minimum period of ten (10) years from the transaction date in tamper-evident electronic archives.

5.2. Statutory Penalties:
Failure to adhere to these directions will attract statutory penalties under Section 47A(1)(c) of the Banking Regulation Act, 1949, including pecuniary fines up to 10,000,000 INR and potential suspension of authorized dealer category banking licenses.
```

---

## 6. Justification of Chunk Size (400) and Overlap (60)

### Why 400 Tokens?
- **Domain Fit for Regulatory Text:** Regulatory circulars (e.g., RBI, Basel, SEC, FINRA) typically group actionable rules into numbered paragraphs spanning 150–350 tokens. A 400-token ceiling accommodates an entire sub-rule alongside its immediate caveats and statutory references without forcing unnecessary mid-clause splits.
- **Precision vs. Context Trade-Off:** Larger chunks (800–1,500 tokens) dilute embedding similarity by blending disparate compliance rules, reducing vector retrieval accuracy. Smaller chunks (100–200 tokens) isolate sentences from their operative definitions, exceptions, and penalty clauses. A 400-token window balances specificity with self-contained context.
- **Prompt Budget Integration:** Consider a standard RAG prompt formula:
  $$\text{Context Demand} = \text{System Prompt} + \text{User Question} + \text{Chat History} + (k \times \text{Chunk Size}) + \text{Reserved Output}$$
  With $k=4$ retrieved chunks of 400 tokens each, context consumption is $\approx 1,600$ tokens, leaving ample room within standard 8K, 16K, or 128K context budgets for conversational history and structured JSON outputs.

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
RBI/2024-25/108
NOTIFICATION: MASTER DIRECTION – WIRE TRANSFER MONITORING AND CUSTOMER DUE DILIGENCE
Effective Date: April 1, 2024
Review Date: 2026-03-31
Issuing Authority: Reserve Bank of India, Department of Banking Regulation

Section 1. Legislative Authority & Scope
In exercise of the powers conferred by Section 35A of the Banking Regulation Act, 1949, the Reserve Bank of India hereby issues these mandatory directives to all Regulated Entities (REs), including commercial banks, cooperative societies, payment aggregators, and authorized non-banking institutions operating payment corridors.

The RE's audit team shall review compliance with these guidelines on a quarterly basis. Every bank's board of directors must record the compliance officer's annual declaration of conformance and verify that automated transaction screening algorithms are audited by a CERT-In empanelled auditor.

Section 2. Mandatory Thresholds for Cross-Border Transactions

2.1. Customer Due Diligence (CDD) Requirements:
1. All cross-border wire transfers exceeding $10,000 USD (or foreign currency equivalent) require complete originator and beneficiary verification prior to fund execution.
2. Cash transactions exceeding 50,000 INR require verification of Permanent Account Number (PAN) or Form 60 declaration.
3. Wire transfers initiated for high-risk accounts shall be subject to mandatory Enhanced Due Diligence (EDD) under Rule 14.2(c).
4. Intermediary institutions involved in multi-hop correspondent payment routing must retain all technical wire messaging headers (SWIFT MT103 / ISO 20022 message structures) intact throughout transmission.

Section 3. Sanctions Screening and Safe-Harbor Clearance Protocols

3.1. General Prohibition and Safe-Harbor Exemption:
Regulated entities maintaining correspondent banking corridors are strictly prohibited from executing wire transfers linked to designated jurisdictions, UNLESS the transferring institution obtains a verified statutory clearance certificate issued by the Financial Intelligence Unit (FIU-IND) within twenty-four hours of transaction initiation.

Section 4. Capital Adequacy and Risk-Weighted Reserve Requirements

Regulated entities maintaining cross-border remittance facilities must preserve supplementary tier-1 liquid buffers against settlement latency and currency variance.

| Capital Tier | Minimum CET1 Ratio | Capital Conservation Buffer | Countercyclical Buffer |
| Tier 1 Primary | 5.5% | 2.5% | 0.0% - 2.5% |
| Tier 2 Subordinated | 2.0% | N/A | N/A |
| Total Regulatory Capital | 9.0% | 2.5% | Dynamic Countercyclical |

Section 5. Record Retention, Reporting Protocols, and Penal Sanctions

5.1. General Rule:
All records of transactions, account-opening dossiers, identity credentials, and beneficial ownership declarations shall be preserved for a minimum period of ten (10) years from the transaction date in tamper-evident electronic archives.

5.2. Statutory Penalties:
Failure to adhere to these directions will attract statutory penalties under Section 47A(1)(c) of the Banking Regulation Act, 1949, including pecuniary fines up to 10,000,000 INR and potential suspension of authorized dealer category banking licenses.
```
