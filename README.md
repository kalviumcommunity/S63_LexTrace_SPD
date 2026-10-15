# ChronoLex

## Tagline

> **Find the rule. Know when it applied. See why.**

---

## Problem Statement

A large bank maintains thousands of compliance circulars, regulatory advisories (e.g., RBI, SEC, Basel Committee), internal audit directives, and policy updates. When evaluating a specific transaction—such as a cross-border remittance, credit authorization, or high-value correspondent account operation—risk and compliance officers face a significant bottleneck:

- **Historical Contradictions & Amendments**: Regulations are frequently amended, clarified, or superseded over time. A circular issued in 2021 might be modified by an addendum in 2023 and partially revoked in 2024.
- **Time Inconsistency**: Compliance officers cannot simply ask *"What is the rule?"*—they must determine *"What rule was in force on the exact date of this transaction?"*
- **Audit Risk & Hallucination**: Generic AI tools or manual skim-reading can introduce hallucinations or miss critical carve-outs. Audits demand line-item traceability back to the authoritative text, circular paragraph, and effective date.

Compliance officers currently spend hours manually reconciling conflicting historical PDFs, exposing the institution to compliance breaches, regulatory fines, and operational delays.

---

## Proposed Solution

**ChronoLex** is a time-aware, source-grounded Retrieval-Augmented Generation (RAG) assistant tailored specifically for banking compliance and risk officers.

Instead of relying on general LLM memory, ChronoLex anchors every answer in the organization's verified document repository. By indexing regulatory documents alongside temporal metadata (`effective_from`, `effective_to`, `supersedes_id`, `issuing_authority`), ChronoLex performs date-scoped semantic retrieval to identify the exact rule governing any transaction date, synthesizing clear explanations with verifiable line-by-line citations and explicit refusal guardrails when evidence is insufficient.

---

## Core Idea

The end-to-end information flow follows a rigorous RAG pipeline:

```
Regulatory Documents (PDFs, Circulars, Directives)
   │
   ▼
Text Extraction (Layout-aware document parsing)
   │
   ▼
Cleaning & Normalization (Header/footer stripping, boilerplate removal)
   │
   ▼
Intelligent Chunking (Hierarchical section & clause boundary splitting)
   │
   ▼
Metadata Enrichment (Source, Circular No., Effective Date, Authority, Status)
   │
   ▼
Embedding Generation (Dense vector representations via embedding model)
   │
   ▼
Vector Database (ChromaDB collection with payload metadata index)
   │
   ▼
Time-Aware Retrieval (Semantic similarity + Temporal date-range filtering)
   │
   ▼
Context Injection (Assembled prompt with strictly bounded evidence)
   │
   ▼
LLM Generation (Deterministic reasoning instructions)
   │
   ▼
Grounded Answer + Citations (Exact circular, section, paragraph, and date)
```

---

## Key Features

| Feature | Status | Description |
|---|---|---|
| **OpenAI-Compatible LLM API Access** | 🟢 **Implemented** | Configurable client, chat completions, usage tracking, backoff & error handling. |
| **Token Estimation & Cost Budgeting** | 🟢 **Implemented** | Tiktoken token counting, cost modeling, context window budgeting, and corpus scaling. |
| **Structured Output & JSON Validation** | 🟢 **Implemented** | Strict schema validation, Pydantic enforcement, bounded 1-retry recovery, and POST /api/llm/structured. |
| **Regulatory Document Ingestion** | ⏳ *Planned (Week 2)* | Automated ingestion of multi-page PDF circulars and regulatory directives. |
| **PDF Text Extraction & Cleaning Pipeline** | 🟢 **Implemented** | Conservative layout-aware cleaner, NFKC, page-number & header/footer removal, safe mojibake repair, and batch corpus processing. |
| **Intelligent Chunking** | ⏳ *Planned (Week 2)* | Clause-aware token chunking with sliding overlap to maintain regulatory context. |
| **Metadata & Provenance Tracking** | ⏳ *Planned (Week 2)* | Attribution tagging for circular number, issuing authority, and effective date ranges. |
| **Embedding Generation** | ⏳ *Planned (Week 3)* | Batch vector generation using OpenAI-compatible embedding models. |
| **Semantic & Top-K Retrieval** | ⏳ *Planned (Week 3)* | Cosine distance similarity search across indexed regulatory chunk vectors. |
| **Time-Aware / Metadata Filtering** | ⏳ *Planned (Week 3)* | Hard date-boundary queries (`transaction_date BETWEEN effective_from AND effective_to`). |
| **RAG Pipeline & Context Injection** | ⏳ *Planned (Week 4)* | Structured prompt synthesis binding retrieved evidence to LLM reasoning. |
| **Source Citation & Attribution** | ⏳ *Planned (Week 4)* | Traceable references linking statements to specific circulars and paragraphs. |
| **Hallucination Guardrails & Refusal** | ⏳ *Planned (Week 4)* | Deterministic fallback refusing to guess when evidence is missing or ambiguous. |
| **Conflict & Version Resolution** | ⏳ *Planned (Week 4)* | Explicit detection of superseded circulars vs. currently active directives. |
| **Interactive Query Interface** | ⏳ *Planned (Week 5)* | Next.js chat interface with streaming answers and interactive citation inspectors. |
| **RAG Evaluation & Monitoring** | ⏳ *Planned (Week 5)* | Automated benchmarking for faithfulness, answer relevance, and retrieval recall. |

*Status Legend:*
- 🟢 **Initialized**: Scaffolding, verification endpoints, and foundation complete.
- ⏳ **Planned**: Scheduled for implementation during subsequent sprint milestones.

---

## Architecture

```mermaid
flowchart LR
    subgraph DataIngestion ["1. Ingestion Pipeline (Offline)"]
        A[Regulatory Documents & Circulars] --> B[Text Extraction & Cleaning]
        B --> C[Intelligent Chunking + Metadata]
        C --> D[Dense Embedding Generation]
        D --> E[(Vector Database: ChromaDB)]
    end

    subgraph QueryExecution ["2. Query Pipeline (Online)"]
        F[Compliance Officer Query] --> G[Query & Date Parser]
        G -->|Time-Filtered Semantic Search| E
        E -->|Top-K Relevant Chunks| H[Context Assembly & Injection]
        H --> I[OpenAI-Compatible LLM]
        I --> J[Grounded Answer + Citations]
    end

    subgraph ClientLayers ["3. Client & Presentation"]
        K[Next.js Web Interface] <-->|REST API| L[FastAPI Backend]
        L --> QueryExecution
    end
```

---

## Technology Stack

| Technology | Role | Rationale |
|---|---|---|
| **Python 3.11+** | Backend & AI Runtime | De facto standard for AI, NLP, document parsing, and RAG pipelines. |
| **FastAPI** | Backend Web Framework | High-performance asynchronous REST API with automatic OpenAPI documentation and native Pydantic validation. |
| **Next.js 16 (React 19)** | Frontend Web Framework | Fast, server-rendered and client-interactive UI supporting modern React paradigms and streaming responses. |
| **TypeScript** | Frontend Language | Static type safety ensuring contract consistency across API interactions and citation rendering. |
| **Tailwind CSS** | Styling | Modern, utility-first styling for dark-mode interfaces, crisp typography, and high-density compliance data views. |
| **OpenAI-Compatible LLM API** | Inference Provider | Industry-standard API surface (`/v1/chat/completions`) enabling flexible model switching (OpenAI, local Ollama, vLLM, or Azure). |
| **Embedding Model** | Vector Representation | Dense semantic representations (e.g., `text-embedding-3-small`) capturing legal and financial nuances. |
| **ChromaDB** | Vector Database | Selected for development and local embedded persistence with zero external service overhead, combined with native metadata filtering. (See [ADR 0001](file:///Users/prithvisingh/Documents/S63_LexTrace_SPD/docs/decisions/0001-vector-database-selection.md)). |
| **Git & GitHub** | Version Control | Standard collaborative workflow with feature branching and auditable change logs. |

---

## Repository Structure

```
ChronoLex/
│
├── apps/
│   ├── api/                     # Python FastAPI Backend
│   │   ├── app/
│   │   │   ├── main.py          # FastAPI application entrypoint & health routes
│   │   │   ├── api/             # REST route controllers (future endpoints)
│   │   │   ├── core/            # App configuration and environment loading
│   │   │   ├── models/          # Pydantic data models & schemas
│   │   │   ├── services/        # RAG, retrieval, embedding, and LLM services
│   │   │   └── utils/           # Shared utility functions
│   │   ├── tests/
│   │   │   └── test_main.py     # API unit tests
│   │   ├── requirements.txt     # Python backend dependencies
│   │   └── README.md            # API documentation
│   │
│   └── web/                     # Next.js TypeScript Frontend
│       ├── app/
│       │   ├── layout.tsx       # Root layout, fonts, and dark theme
│       │   ├── page.tsx         # ChronoLex landing and status verification
│       │   └── globals.css      # Tailwind design system tokens
│       ├── components/          # Reusable UI components
│       ├── lib/                 # Client utilities and helpers
│       ├── public/              # Static assets
│       ├── package.json         # Node.js dependencies
│       └── README.md            # Frontend documentation
│
├── data/
│   ├── raw/                     # Original regulatory PDFs and circulars (.gitkeep)
│   ├── processed/               # Cleaned corpora and extracted chunk JSONs (.gitkeep)
│   └── README.md                # Data management and governance rules
│
├── docs/
│   ├── architecture/
│   │   └── overview.md          # Architectural diagrams and deep-dive
│   ├── decisions/
│   │   └── 0001-vector-database-selection.md  # Vector database selection ADR
│   └── README.md                # Documentation catalog
│
├── scripts/
│   └── README.md                # Data ingestion, indexing, and eval helper scripts
│
├── .env.example                 # Sanitized environment variable template
├── .gitignore                   # Multi-language ignore rules (Python, Node, Vector DB)
├── LICENSE                      # MIT Open Source License
└── README.md                    # Project master documentation (this file)
```

---

## Sprint 2 Concept Mapping

The ChronoLex project maps directly onto the 40 core concepts of **Sprint #2 — AI Application Development with RAG**:

| # | Sprint Concept | ChronoLex Implementation |
|---|---|---|
| 1–2 | Dev Environment & Git Workflow | Monorepo layout, FastAPI, Next.js, `.env.example`, Git feature branches |
| 3–6 | LLM API, Prompts & JSON Output | OpenAI-compatible service, strict system prompts, citation JSON schemas |
| 7–12 | Document Loading, Cleaning & Chunking | Regulatory PDF parsing (`data/raw`), clause chunking, metadata tags (`effective_from`, `authority`) |
| 13–17 | Embeddings, Metrics & Quality Checks | Dense embeddings generation, cosine similarity verification, cost estimation |
| 18–21 | Vector Database & Metadata Search | ChromaDB embedded storage, temporal filtering (`WHERE date BETWEEN ...`) |
| 22–24 | Retrieval Tuning & Re-ranking | Hybrid search tuning, Top-K precision, cross-encoder re-ranking evaluation |
| 25–29 | RAG Pipeline, Grounding & Guardrails | Context assembly, strict quote grounding, refusal for missing regulatory evidence |
| 30–31 | Conversational RAG & Evaluation | Multi-turn query clarification, Ragas/faithfulness metric benchmarks |
| 32–36 | Backend API & Streaming Chat UI | `/api/v1/query`, SSE streaming answers, responsive Next.js compliance UI |
| 37–40 | Monitoring, Deployment & Docs | Token usage logs, container deployment readiness, architecture guides |

---

## Development Roadmap

The project is developed incrementally across the 5-week Sprint 2 schedule:

- **Week 1: Foundations & Architecture (Current)**
  - Repository initialization, monorepo structure, verification endpoints, landing page, environment configuration, and vector database selection ADR.
- **Week 2: Corpus Ingestion & Intelligent Chunking**
  - Banking circular ingestion (`data/raw/`), PDF extraction, noise cleaning, time-aware metadata extraction, and chunking with overlap.
- **Week 3: Embeddings & Vector Storage**
  - Embedding pipeline integration, ChromaDB collection setup, indexing, similarity search, and date-filtered retrieval.
- **Week 4: RAG Pipeline, Grounding & Guardrails**
  - Prompt engineering, strict context injection, grounded answer generation, verifiable citation linking, and refusal guardrails.
- **Week 5: UI Integration, Streaming, Evaluation & Deployment**
  - Full-stack integration with Next.js interactive chat interface, streaming responses, citation drawers, retrieval evaluation benchmarks, and deployment.

---

## Local Development

### Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 20.x or higher
- **npm**: 10.x or higher

---

### 1. Clone & Configure Environment

```bash
git clone https://github.com/kalviumcommunity/S63_LexTrace_SPD.git ChronoLex
cd ChronoLex

# Copy environment variables template
cp .env.example .env
```

---

### 2. Backend Setup (FastAPI)

```bash
cd apps/api

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify backend:
- Root status: [http://localhost:8000/](http://localhost:8000/)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Run tests: `pytest`

---

### 3. Frontend Setup (Next.js)

```bash
cd apps/web

# Install dependencies
npm install

# Start development server
npm run dev
```

Verify frontend:
- Open [http://localhost:3000](http://localhost:3000)
- Build check: `npm run build`
- Lint check: `npm run lint`

---

## Git Workflow

To maintain code hygiene and collaborative standards, ChronoLex adopts a branch-based development lifecycle:

- `main`: Production-ready, verified code. All sprint milestones land here via pull requests.
- `develop`: Integration branch for active weekly sprint milestones.
- Feature branches:
  - `feature/llm-api-integration`: Sprint #2 OpenAI-compatible LLM client integration, chat completion, error handling, and demonstration.
  - `feature/document-ingestion`: Week 2 PDF parsing and chunking.
  - `feature/embeddings`: Week 3 vector database and embeddings.
  - `feature/retrieval`: Week 3 time-aware retrieval and filtering.
  - `feature/rag-pipeline`: Week 4 context injection and grounded generation.
  - `feature/compliance-ui`: Week 5 Next.js chat interface and citation display.

---

## LLM API Integration

### Overview
The LLM API integration connects ChronoLex to any OpenAI-compatible large language model provider (such as OpenAI, Ollama, vLLM, OpenRouter, Azure OpenAI, or LocalAI). It provides:
- A standardized, decoupled configuration mechanism via environment variables.
- A reusable Python service module (`app.services.llm.LLMService`) for constructing and dispatching chat completion requests.
- Automatic extraction and structured parsing of message contents and token usage metadata.
- Request/response logging and usage monitoring via Python's standard `logging` module with zero credential exposure.
- Robust, differentiated error handling for common API failure modes (HTTP 401 Unauthorized, HTTP 429 Rate Limiting, connection timeouts, and provider errors) with bounded exponential backoff.
- A FastAPI endpoint (`POST /api/llm/chat`) exposing the completion service with input validation and clean error status mappings.
- A standalone, executable demonstration script (`scripts/demo_llm.py`).

> **Note**: This sprint milestone focuses strictly on foundational LLM client integration and error resilience. Document parsing, embedding generation, vector indexing, and end-to-end RAG retrieval pipelines are scheduled for subsequent sprint milestones.

### Request-Response Cycle & Architecture
The integration follows a clear client-service-provider lifecycle:

1. **Client / Caller**: A client issues a prompt via the FastAPI endpoint `POST /api/llm/chat` or the CLI demonstration script.
2. **Validation**: The input message is validated (rejecting empty or whitespace-only inputs with HTTP 422/400).
3. **Payload Construction**:
   - **`system` message**: Configures the persona, tone, and behavioral boundaries of the model (default: `"You are a concise assistant."`).
   - **`user` message**: Encapsulates the specific instruction or question provided by the end user.
   - **`model`**: Specifies the targeted LLM model identifier (e.g., `gpt-4o-mini`, `mistral`, `llama3`).
4. **Logging & Dispatch**: The service logs the request messages at `INFO` level (ensuring API keys and authorization headers are never logged) and invokes `client.chat.completions.create(...)`.
5. **Response Extraction**: The generated text is safely extracted from `response.choices[0].message.content`. Model metadata and token usage (`prompt_tokens`, `completion_tokens`, `total_tokens`) are parsed into a structured `TokenUsage` schema.
6. **Error Handling & Backoff**: If rate limits or network issues arise, bounded exponential backoff retries transient failures. If authentication fails, a sanitized 401 error is logged and returned immediately without leaking credentials.

### Environment Configuration
The service is configured using standard environment variables loaded via `python-dotenv`:

| Environment Variable | Description | Default / Example |
|---|---|---|
| `OPENAI_API_KEY` | Provider API authentication token | *(Required for live API calls)* |
| `OPENAI_BASE_URL` | Base URL of the OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `CHAT_MODEL` | Model identifier to target | `gpt-4o-mini` |
| `OPENAI_MODEL` | Backwards-compatible alias for `CHAT_MODEL` | `gpt-4o-mini` |

To configure your environment:
```bash
cp .env.example .env
```
Edit `.env` and set your credentials:
```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
CHAT_MODEL=gpt-4o-mini
```

#### Substituting OpenAI-Compatible Providers
Because `OPENAI_BASE_URL` is configurable, any OpenAI-compatible provider or local runtime can be used without code modifications:
- **Ollama (Local)**:
  ```env
  OPENAI_BASE_URL=http://localhost:11434/v1
  OPENAI_API_KEY=ollama
  CHAT_MODEL=llama3
  ```
- **vLLM / LocalAI**:
  ```env
  OPENAI_BASE_URL=http://localhost:8000/v1
  OPENAI_API_KEY=dummy
  CHAT_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
  ```
- **OpenRouter**:
  ```env
  OPENAI_BASE_URL=https://openrouter.ai/api/v1
  OPENAI_API_KEY=sk-or-v1-...
  CHAT_MODEL=openai/gpt-4o-mini
  ```

### Error Handling & Resilience
The integration handles errors explicitly using the OpenAI SDK exception hierarchy:

- **HTTP 401 Unauthorized (`AuthenticationError`)**:
  - Logged as: `"Authentication failed (401): Check OPENAI_API_KEY and provider credentials."`
  - Sanitized message returned to client; sensitive credentials or tokens are never leaked.
- **HTTP 429 Rate Limiting (`RateLimitError`)**:
  - Logged as: `"Rate limited (429): Check provider rate limits or quota and retry appropriately."`
  - Transient rate limits undergo bounded exponential backoff (up to 2 retries). Quota exhaustion errors terminate immediately without pointless retries.
- **Connection & Timeout Failures (`APIConnectionError`, `APITimeoutError`)**:
  - Mapped to HTTP 502 with retry attempts.
- **Missing Configuration**:
  - Attempting a completion without an API key raises `LLMConfigurationError` with a clear actionable message, mapped to HTTP 500 without crashing unrelated endpoints (such as `/health`).

### Executing the Demonstration Script
Run the demonstration script from the repository root:

```bash
# Activate virtual environment
source apps/api/.venv/bin/activate

# Execute demonstration
python scripts/demo_llm.py
```
If credentials are not yet set in `.env`, the script displays an informative message explaining how to configure credentials without crashing.

### Starting the FastAPI Backend
Start the backend development server:

```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Testing the Chat Completion Endpoint
Send a test POST request to `/api/llm/chat`:

```bash
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Say hello in one sentence."}'
```

Example response:
```json
{
  "answer": "Hello! It is a pleasure to assist you with ChronoLex compliance verification.",
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 14,
    "total_tokens": 29
  }
}
```

### Running Unit & Integration Tests
Automated tests mock all provider interactions so no real API key is required and no charges are incurred:

```bash
# Run tests with pytest
apps/api/.venv/bin/pytest apps/api/tests -v
```

---

## Prompt Engineering Experiments

This section covers prompt design patterns and comparative experiments implemented in ChronoLex:
1. **System vs. User Role Separation**
2. **Vague vs. Specific Prompt Comparisons**
3. **Explicit Output Formatting Constraints (JSON)**
4. **ChronoLex Regulatory Grounding Prompt & Anti-Injection Guardrails**

---

### 1. System vs. User Message Responsibilities
In OpenAI-compatible chat completion APIs, the `system` and `user` roles serve fundamentally distinct purposes:
- **`system` role**: Sets the global persona, scope of authority, tone, operational boundaries, and persistent guardrails (e.g. max response length, refusal instructions when unsure). It governs *how* the model behaves.
- **`user` role**: Delivers the dynamic instruction, query, or task. It governs *what* the model should process in the immediate turn.

Keeping these roles strictly separated prevents prompt leakage, enforces security boundaries, and prevents user inputs from overriding structural behavioral guardrails.

Example:
```json
[
  {
    "role": "system",
    "content": "You are a support assistant for an internal docs tool. Answer in 2 sentences max. If you are unsure, say you don't know."
  },
  {
    "role": "user",
    "content": "What is our refund window?"
  }
]
```

---

### 2. Vague vs. Specific Prompt Comparisons
Prompts with identical underlying intent can produce markedly different responses based on phrasing specificity:
- **Vague Prompt** (`"Explain our refund policy."`): Leaves scope, format, and depth unspecified. The LLM typically responds with broad, verbose overviews covering edge cases, exceptions, and narrative background.
- **Specific Prompt** (`"In one sentence, state the refund window in days."`): Constrains output length, units, and focal topic. The LLM produces a concise, factual answer that can be quickly reviewed or parsed by downstream services.

In automated testing, running both prompts independently against the same model demonstrates how prompt constraints directly control output variance and token expenditure.

---

### 3. Explicit Output Constraints & Structured JSON Parsing
Downstream pipelines (such as automated compliance checks) require predictable machine-readable outputs rather than unstructured prose. Specifying format requirements in the system prompt makes responses deterministic:

```text
Reply with only a valid JSON object containing the keys "answer" and "source".
```

The ChronoLex prompt service (`app.services.prompt_service.parse_json_safely`) parses returned JSON safely using Python's standard `json.loads` rather than insecure `eval()`. It strips potential markdown code fences (` ```json ... ``` `) and gracefully handles malformed JSON without raising unhandled server errors.

*Note on Guaranteed Structured Output*: While system prompt instructions guide the model toward structured outputs, guaranteed schema compliance requires provider-level constrained decoding. ChronoLex gracefully handles providers that do or do not support native JSON mode.

---

### 4. ChronoLex Regulatory Grounding Prompt
For reliable compliance verification, ChronoLex anchors model generation strictly in verified regulatory text:

```text
You are ChronoLex, an assistant for regulatory and compliance research.

Answer only using the regulatory context supplied in the request.
Do not invent regulatory requirements, dates, quotations, or citations.
If the context does not contain enough evidence to answer, explicitly state
that the supplied context is insufficient.
Distinguish what the source states from any interpretation.
When source metadata is supplied, preserve the source name and applicable
date or version.
Be concise, factual, and precise.
```

#### Grounding Guardrails & Delimiters:
- **Context Boundaries**: Evidence is enclosed within explicit `BEGIN CONTEXT` and `END CONTEXT` blocks.
- **Indirect Prompt Injection Defense**: The prompt explicitly instructs the model to treat text inside the context strictly as factual evidence to evaluate, ignoring any imperative instructions or commands embedded within the documents.
- **Empty & Insufficient Context Handling**: If no context is supplied, ChronoLex immediately returns `"The supplied context is insufficient to answer the question."` with `evidence_sufficient = False` without calling the LLM or hallucinating rules.

---

### Environment Configuration
The prompt experiments reuse the existing LLM configuration loaded via `python-dotenv`:

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
CHAT_MODEL=gpt-4o-mini
```

---

### Running the Experiments

#### 1. CLI Demonstration Script
Run the interactive demonstration script covering all four experiments:

```bash
# Activate virtual environment
source apps/api/.venv/bin/activate

# Execute demonstration
python scripts/demo_prompts.py
```

If credentials are not yet configured in `.env`, the script safely demonstrates the prompt structures, role separation, and insufficient-evidence guardrails without crashing.

#### 2. FastAPI Endpoint (`POST /api/llm/prompt-experiment`)
Start the FastAPI server:

```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Send requests for each experiment mode:

- **System vs. User Roles**:
  ```bash
  curl -X POST http://localhost:8000/api/llm/prompt-experiment \
    -H "Content-Type: application/json" \
    -d '{"mode": "system_user"}'
  ```

- **Vague vs. Specific Comparison**:
  ```bash
  curl -X POST http://localhost:8000/api/llm/prompt-experiment \
    -H "Content-Type: application/json" \
    -d '{"mode": "compare"}'
  ```

- **Explicit JSON Constraint**:
  ```bash
  curl -X POST http://localhost:8000/api/llm/prompt-experiment \
    -H "Content-Type: application/json" \
    -d '{"mode": "json"}'
  ```

- **ChronoLex Regulatory Grounding**:
  ```bash
  curl -X POST http://localhost:8000/api/llm/prompt-experiment \
    -H "Content-Type: application/json" \
    -d '{
      "mode": "grounding",
      "question": "How long must KYC records be retained?",
      "context": "RBI Master Direction KYC Section 38: Maintain records for at least 5 years."
    }'
  ```

---

## Tokenization, Cost Estimation & Context Budgets

### 1. What Tokens Are & Why They Differ From Words and Characters
Large Language Models process text as discrete numerical sequences called **tokens**, rather than individual words or characters:
- **Tokens $\neq$ Words $\neq$ Characters**: A word is not guaranteed to produce one token. For example:
  - `"refund"` $\rightarrow$ **1 token** (`[32338]` in `cl100k_base`).
  - `"What is our refund window?"` $\rightarrow$ **6 tokens** (`['What', ' is', ' our', ' refund', ' window', '?']`).
  - Complex terminology, legal Latin, numbers, punctuation, and capitalization break into multiple sub-word tokens (e.g., `"ChronoLex"` $\rightarrow$ 3 tokens).
- **Encoding Differences**: Token counts depend on the tokenizer encoding scheme (`cl100k_base` for GPT-4o / GPT-4 / text-embedding-3, `p50k_base` for code models, `r50k_base` / `gpt2` for earlier architectures). Token counts differ across providers and model families.
- **Provider Overhead vs. Local Estimates**: Local tokenization calculates string tokens accurately, but live provider API requests incur additional chat formatting overhead (`<|im_start|>`, role headers, trailing turn indicators).

### 2. Dependency Setup & Verification
ChronoLex utilizes the high-performance `tiktoken` library for local token counting and offline analysis without requiring paid API keys:

```bash
cd apps/api
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Running the Offline Demonstration Script
The demonstration script (`scripts/token_cost_demo.py`) operates 100% offline without requiring an API key:

```bash
# Run full demonstration with defaults
apps/api/.venv/bin/python scripts/token_cost_demo.py

# Inspect CLI options
apps/api/.venv/bin/python scripts/token_cost_demo.py --help

# Evaluate custom token counts and pricing
apps/api/.venv/bin/python scripts/token_cost_demo.py \
  --input-tokens 2500 \
  --output-tokens 600 \
  --input-price 0.0005 \
  --output-price 0.0015

# Count tokens in a specific document or directory
apps/api/.venv/bin/python scripts/token_cost_demo.py --file path/to/document.txt
apps/api/.venv/bin/python scripts/token_cost_demo.py --docs-dir path/to/docs/
```

### 4. Counting Tokens in Files & `data/policy.txt`
The utility checks for `data/policy.txt` in the repository root:
- If `data/policy.txt` is missing, ChronoLex does **not** create fake content. It clearly logs that the file is not found and instructs the user how to supply a UTF-8 text file.
- To analyze a policy file, create `data/policy.txt` with your compliance text or pass `--file <path>`.

### 5. API Cost Estimation Formula
Estimated API costs are calculated using prompt and completion token counts with model-specific rates per 1,000 tokens:

$$\text{Total Cost} = \left(\frac{\text{Input Tokens}}{1,000} \times \text{Input Price per 1k}\right) + \left(\frac{\text{Output Tokens}}{1,000} \times \text{Output Price per 1k}\right)$$

- **Illustrative Rates**: ChronoLex demonstrates with illustrative default rates ($0.0005 per 1,000 input tokens; $0.0015 per 1,000 output tokens). **These are illustrative defaults and must be replaced with verified, model-specific provider pricing.**
- **Non-Negative Validation**: All token counts and price rates are validated to be non-negative.
- **Zero-Usage & Edge Cases**: Correctly supports zero tokens, input-only completions, and output-only generation without precision loss.

### 6. Provider-Reported Usage vs. Local Estimates
When live LLM requests succeed:
- ChronoLex extracts `response.usage.prompt_tokens`, `completion_tokens`, and `total_tokens` directly from the provider response.
- If model-specific pricing (`LLM_INPUT_PRICE_PER_1K` and `LLM_OUTPUT_PRICE_PER_1K`) is configured in the environment or passed at runtime, `TokenUsage.estimated_cost` is calculated and attached.
- If rates are not configured or the provider omits usage data, ChronoLex gracefully retains `None` without inventing numbers or failing.

### 7. Context-Window Budgeting
Before sending large regulatory prompts to the LLM, ChronoLex evaluates request fit against a configured context budget:
- **Components Tracked**:
  1. System prompt tokens
  2. User question tokens
  3. Retrieved context tokens (regulatory circular excerpts)
  4. Conversation history tokens (prior turns)
  5. Reserved output tokens (budgeted for LLM generation)
  6. Safety margin buffer (for chat format overhead and tokenizer variance)
- **Overage Reporting**: When total demanded tokens exceed the model context window limit, ChronoLex flags `fits_budget: false` and calculates the exact overage so the retrieval pipeline can adjust chunk selection rather than silently truncating text.

### 8. Corpus-Scale Token and Cost Scaling (4,000 Documents)
To plan storage, vector indexing, and runtime RAG budgets across large corpora:
- **Corpus Statistics**: Calculates total documents, total token volume, average tokens per document, and min/max lengths.
- **4,000 Document Projection**: For a regulatory corpus of 4,000 documents averaging ~750 tokens per snippet:
  - Total Corpus Tokens: $\approx 3,000,000\text{ tokens}$.
  - Hypothetical Chat Input Cost: $\approx \$1.50$ (at $\$0.0005$ per 1k input tokens).
- **Critical Architectural Distinction**:
  1. **Local Tokenization**: Fast, offline counting via `tiktoken`. Zero API cost.
  2. **Embedding Ingestion**: One-time cost to transform documents into dense vector representations for ChromaDB indexing.
  3. **Chat Generation**: Recurring per-query cost where only the top-$k$ retrieved chunks ($\sim 1,000\text{--}2,000\text{ tokens}$) are sent into the LLM context window—*never* all 4,000 documents at once.

### 9. FastAPI Endpoint (`POST /api/llm/token-estimate`)
The API exposes an endpoint for token estimation, pricing calculations, and context budgeting:

```bash
curl -X POST http://localhost:8000/api/llm/token-estimate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is our refund window?",
    "encoding": "cl100k_base"
  }'
```

Response:
```json
{
  "encoding": "cl100k_base",
  "token_count": 6,
  "text_length_chars": 26,
  "cost_estimate": null,
  "budget_estimate": null
}
```

---

Response:
```json
{
  "encoding": "cl100k_base",
  "token_count": 6,
  "text_length_chars": 26,
  "cost_estimate": null,
  "budget_estimate": null
}
```

---

## Structured Output & JSON Validation

### 1. Why Structured Output is Critical for Compliance Applications
In an enterprise regulatory assistant like ChronoLex, model responses cannot remain unstructured free-form prose. Downstream systems—including audit trails, workflow orchestrators, automated risk classifiers, and frontend inspectors—require strict, predictable data contracts.
- **Fragility of Free-Form Prose**: Parsing prose with regular expressions or heuristics is brittle, sensitive to phrasing nuances, and susceptible to hallucinations or conversational filler.
- **Type Safety & Schema Integrity**: Structured JSON output ensures responses conform to explicit field names, required types, and non-empty constraints.
- **Deterministic Downstream Execution**: Strongly typed responses enable programmatic handling, reliable database logging, and direct binding into strongly typed client components.

---

### 2. How the System Prompt Enforces Fixed JSON Schemas
ChronoLex enforces structured output at the prompt layer by employing a strict system instruction:

```
Reply with ONLY a JSON object containing the keys "answer" and "source". Do not include any additional prose.
```

- **Role Separation**: The system prompt defines the data contract and format constraints, while the user message conveys the compliance inquiry.
- **Anti-Prose Directives**: Explicit instructions instruct the model to omit Markdown code fences, conversational greetings, and post-generation disclaimers.
- **Deterministic Sampling**: The LLM is invoked with `temperature=0.0` when supported by the configured model to minimize token variance and ensure repeatable, structured generation.

---

### 3. JSON Mode: Capabilities and Critical Boundaries
When supported by the underlying OpenAI-compatible provider, ChronoLex supplies `response_format={"type": "json_object"}`.

#### Critical Distinction: Syntax Guarantee vs. Schema Validity
> [!IMPORTANT]
> **JSON mode guarantees valid JSON syntax, but it does NOT guarantee schema conformance or factual accuracy.**
> - **What JSON mode does**: Constrains the token generation probability distribution so the output parses without a syntax error (`json.loads()` will not raise `JSONDecodeError`).
> - **What JSON mode does NOT do**: It does **not** verify that required keys (`answer`, `source`) are present, that values are non-empty strings rather than numbers or lists, or that the content is factually accurate or grounded in regulatory reality.
> - **Necessity of Application-Layer Validation**: Local parsing and Pydantic validation remain mandatory even when JSON mode is active.

#### Graceful Provider Fallback
Certain proxy providers, self-hosted endpoints, or specialized models (e.g. reasoning models) reject `response_format={"type": "json_object"}` with HTTP 400 (`unsupported parameter`).
- ChronoLex detects unsupported `response_format` errors without crashing or entering infinite loops.
- The service gracefully falls back to explicit prompt instructions combined with local parsing and validation.

---

### 4. Parsing and Validation: `json.loads()` and Pydantic
ChronoLex implements a two-stage parsing and validation pipeline:

```
Raw Model String
       │
       ▼
1. Clean & Strip Markdown Fences (```json ... ```)
       │
       ▼
2. Python json.loads() ────[Syntax Error]───► Malformed Error
       │
       ▼
3. Enforce Dict / JSON Object ───[List / Primitive]──► Type Error
       │
       ▼
4. Check Required Keys ("answer", "source") ───[Missing Keys]──► Missing Field Error
       │
       ▼
5. Pydantic Schema Validation (StructuredAnswer)
       ├─ Strict String Types (strict=True)
       ├─ Non-Empty & Whitespace-Only Rejection
       └─ [Validation Failure] ───► Schema Validation Error
       │
       ▼
Validated StructuredAnswer Model
```

#### The Reusable Parser (`app.utils.json_parsing.parse_response`):
- Strips surrounding Markdown code fences if the model wraps JSON.
- Parses with Python's native `json.loads()`.
- Verifies that the root object is a `dict`, explicitly rejecting JSON arrays (`[...]`) and primitives (`"string"`, `42`, `true`).
- Confirms the presence of all required fields before schema instantiation.
- Never uses `eval()` or dangerous deserializers.

#### Pydantic Model (`app.models.structured.StructuredAnswer`):
```python
from pydantic import BaseModel, ConfigDict, Field, field_validator

class StructuredAnswer(BaseModel):
    model_config = ConfigDict(strict=True)

    answer: str = Field(min_length=1, description="The generated answer.")
    source: str = Field(min_length=1, description="The source or evidence reference.")

    @field_validator("answer", "source")
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Field must be a string.")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace-only.")
        return stripped
```

---

### 5. Bounded Error Recovery & Single-Retry Policy
Models occasionally produce malformed syntax, truncate JSON, or omit required keys. ChronoLex implements a resilient, bounded recovery mechanism:

1. **Attempt 1**: The query is sent with strict system prompts, `temperature=0`, and JSON mode.
2. **Local Evaluation**: The output is evaluated by `parse_response` and Pydantic validation.
3. **Bounded Retry (At Most Once)**:
   - If parsing or schema validation fails, ChronoLex initiates **exactly one** recovery retry (`retries = 1`).
   - The retry conversation appends the assistant's invalid output and a targeted reminder:
     `"Your previous response failed validation: <reason>. Please reply with ONLY a valid JSON object containing keys ['answer', 'source']."`
4. **Permanent Failure Handling**:
   - If the retry succeeds, the validated object is returned with `retries: 1`.
   - If the retry fails, ChronoLex raises `StructuredOutputError` and returns HTTP 422 Unprocessable Content. Unvalidated model output is **never** returned as a successful response.
5. **Immediate Failure on Non-Retryable Errors**: Permanent errors—such as HTTP 401 Authentication errors or missing configuration—fail immediately with 0 retries.

#### Why Retrying is Limited to Exactly One Attempt
- **Latency & Cost Bounding**: Repeated retries multiply token consumption and inflate API costs.
- **Runaway Loop Prevention**: If a deterministic prompt (`temperature=0`) with explicit reminder fails twice, subsequent retries are statistically unlikely to succeed.
- **Fail-Fast Integrity**: Enterprise compliance pipelines require fast, deterministic failure signals rather than prolonged hanging requests.

---

### 6. Regulatory Caution: Model Attribution vs. Verified Citations
> [!CAUTION]
> In standalone demonstration mode (without an active retrieval pipeline), the model-generated `source` field represents **model-reported attribution**, not an authoritative regulatory citation.
> ChronoLex strictly prevents treating model-invented sources as legal evidence until verified by the layout-aware retrieval pipeline (scheduled for Milestone 4).

---

### 7. FastAPI Endpoint (`POST /api/llm/structured`)
The API exposes an endpoint for requesting validated structured answers:

```bash
curl -X POST http://localhost:8000/api/llm/structured \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the typical timeline for filing a Suspicious Activity Report (SAR)?"
  }'
```

#### Successful Response (`200 OK`):
```json
{
  "answer": "Suspicious Activity Reports (SARs) must generally be filed within 30 calendar days of the initial detection of facts that may constitute a basis for filing.",
  "source": "31 CFR 1020.320 / FinCEN SAR Regulations",
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 34,
    "total_tokens": 76,
    "estimated_cost": null
  },
  "retries": 0
}
```

#### Validation Failure Response (`422 Unprocessable Content`):
```json
{
  "detail": {
    "error": "Structured output validation failed",
    "message": "Model output failed structured JSON validation after 1 retry: missing fields: ['source']",
    "validation_error": "missing fields: ['source']",
    "retries": 1
  }
}
```

---

### 8. Running the Demonstration and Tests

#### Running the Demonstration Script
Execute the offline demonstration script covering valid parsing, markdown stripping, schema validation, and bounded retry recovery:

```bash
apps/api/.venv/bin/python scripts/demo_structured.py
```

#### Running the Automated Test Suite
Run the comprehensive test suite verifying parser rules, Pydantic constraints, bounded error recovery, authentication isolation, and API endpoints (100% mocked offline):

```bash
apps/api/.venv/bin/pytest apps/api/tests/test_structured.py -v
```

Run all tests across the ChronoLex backend:

```bash
apps/api/.venv/bin/pytest apps/api/tests -v
```

---

## Text Extraction & Cleaning Pipeline

ChronoLex implements a modular, conservative, layout-aware text cleaning pipeline designed specifically for banking circulars, compliance directives, and statutory regulatory documents.

```mermaid
flowchart TD
    A[Raw Extracted Document / PDF Text] --> B[Stage 1: Unicode NFKC & CRLF Normalization]
    B --> C[Stage 2: Standalone Page-Number Stripping]
    C --> D[Stage 3: Repeated Header & Footer Removal]
    D --> E[Stage 4: Whitespace & Paragraph Normalization]
    E --> F[Cleaned Document Corpus Ready for Chunking]
```

### 1. Why Raw Extracted Text Harms Retrieval Quality
Extracted text from regulatory PDFs frequently contains recurrent noise that severely degrades downstream RAG performance:
- **Embedding Distortion**: Repeating headers on every page (e.g., `"RESERVE BANK OF INDIA - COMPLIANCE BULLETIN"`) dominate semantic vector representations, artificially inflating cosine similarity for irrelevant chunks.
- **Context Fragmentation**: Standalone page numbers (`"Page 4 of 20"`) and broken mid-sentence page boundaries interrupt regulatory clauses, causing embedding models to lose syntactic continuity across sentences.
- **Token Budget Waste**: Repeated navigation banners, web URLs, and blank lines consume scarce LLM context tokens without contributing evidence.
- **Citation Inaccuracies**: Extracted boilerplate can be mistakenly cited by the LLM as authoritative regulatory text.

---

### 2. Unicode NFKC Normalization & Safe Mojibake Repairs
Text is processed through Unicode NFKC (`unicodedata.normalize("NFKC", text)`):
- **What NFKC Does**: Normalizes compatibility characters—such as ligatures (`ﬁ` → `fi`), full-width characters (`Ａ` → `A`), and non-breaking spaces (`\u00a0` → space)—into standard canonical representations.
- **What NFKC Cannot Fix**: NFKC **cannot repair mojibake** caused by decoding UTF-8 bytes as Windows-1252 or ISO-8859-1 (e.g., `â€™` for `’` or `â€œ` for `“`).
- **Safe Mojibake Repair**: ChronoLex applies a targeted dictionary of high-confidence replacements for common quotation, dash, and currency misinterpretations (`KNOWN_MOJIBAKE_REPLACEMENTS`). It deliberately **avoids blind re-encoding**, preventing catastrophic data corruption on mixed-encoding or already valid documents.

---

### 3. Page-Number Boilerplate Removal
ChronoLex removes standalone page numbers using strict line-oriented regex matching:
- **Patterns Handled**: Standalone lines like `Page 3 of 12`, `Page 1`, `- Page 4 of 20 -`, `— Page 5 —`, `[Page 2]`, and `pg. 7`.
- **Inline Citation Protection**: Matching is anchored to full lines (`re.MULTILINE`), ensuring occurrences within paragraphs (e.g., `"refer to page 3 of the annexure"` or `"Section 4: Page limits"`) are **never deleted**.

---

### 4. Repeated Header & Footer Detection
ChronoLex adopts a conservative strategy to detect and remove recurrent noise across pages:
- **Page-Boundary Detection**: Uses form-feed characters (`\x0c`) or explicit section markers emitted by layout-aware document parsers.
- **Frequency-Based Boundary Analysis**: Inspects top and bottom candidate lines across pages. If a line recurs in the header/footer zones across $\ge 2$ pages, it is classified as recurring boilerplate and stripped.
- **Configurable Known Boilerplate**: Allows operators to supply exact strings or regex patterns (e.g., `"CONFIDENTIAL - INTERNAL BANK USE ONLY"`, portal navigation banners).
- **Conservative Protection**: When reliable page boundaries are unavailable, ChronoLex **does not guess** or strip lines solely based on repetition, protecting legitimate repeating regulatory provisions (e.g., recurring section headings or legal formulas).

---

### 5. Whitespace & Structural Normalization
- Collapses consecutive horizontal spaces and tabs into a single ASCII space without merging words.
- Strips trailing whitespace from each line.
- Collapses runs of three or more newlines into standardized double-newlines (`\n\n`), strictly preserving paragraph and clause boundaries.
- Preserves structured lists (`1.`, `2.`, `(a)`), regulatory tables (`| Tier | Ratio |`), section numbers (`Section 3.1(b)`), and calendar dates (`2024-04-01`).

---

### 6. Pipeline Position in Future RAG Architecture

```
Raw Documents (PDF / TXT)
       │
       ▼
Text Extraction (Layout-aware extraction)
       │
       ▼
Text Cleaning & Normalization (ChronoLex Pipeline)  <── [Implemented Here]
       │
       ▼
Intelligent Chunking (Clause & section boundary sliding windows)
       │
       ▼
Dense Embeddings (Vector representation)
       │
       ▼
Vector Database (ChromaDB temporal search)
       │
       ▼
Retrieved Context Injection & Grounded Generation
```

---

### 7. Limitations & Edge Cases
- **Missing Page Boundaries**: In raw single-stream text where PDF page break markers (`\x0c`) are stripped prior to ingestion, auto-detection of headers/footers falls back to explicit known boilerplate patterns to avoid stripping legitimate repeating text.
- **Complex Multi-Column Layouts**: Layout-aware parsing is assumed at the extraction stage before feeding plain text into the cleaning pipeline.

---

### 8. Before/After Evidence and Sample Outputs

A realistic raw sample and its cleaned counterpart are available in the repository:
- **Raw Noisy Sample**: [`data/raw/sample_regulatory_noisy.txt`](file:///Users/prithvisingh/Documents/S63_LexTrace_SPD/data/raw/sample_regulatory_noisy.txt)
- **Cleaned Output**: [`data/processed/sample_regulatory_cleaned.txt`](file:///Users/prithvisingh/Documents/S63_LexTrace_SPD/data/processed/sample_regulatory_cleaned.txt)
- **Before/After Report**: [`docs/examples/cleaning_before_after.md`](file:///Users/prithvisingh/Documents/S63_LexTrace_SPD/docs/examples/cleaning_before_after.md)

---

### 9. Running the Demonstration and Tests

#### Running the Cleaning Demonstration Script
Clean a single file and generate a markdown before/after comparison report:

```bash
apps/api/.venv/bin/python scripts/clean_documents.py \
  --input data/raw/sample_regulatory_noisy.txt \
  --output-dir data/processed \
  --evidence docs/examples/cleaning_before_after.md
```

Clean an entire directory of regulatory documents:

```bash
apps/api/.venv/bin/python scripts/clean_documents.py \
  --input data/raw \
  --output-dir data/processed
```

#### Running Automated Tests
Run the comprehensive cleaning and corpus-processing test suite (100% offline, zero external LLM API dependency):

```bash
apps/api/.venv/bin/pytest apps/api/tests/test_cleaning.py -v
```

---

## Current Status

> **Text Extraction & Cleaning Pipeline complete. Reusable cleaning functions, Unicode NFKC normalization, safe mojibake repair, standalone page-number removal, repeated header/footer detection, whitespace normalization, corpus batch processing, before/after evidence reports, and comprehensive unit tests are fully implemented and verified.**
> 
> *The cleaning pipeline safely preserves all regulatory citations, section numbers, dates, monetary thresholds, and table layouts while removing recurring extraction noise. Ready for downstream intelligent chunking and embedding generation.*

