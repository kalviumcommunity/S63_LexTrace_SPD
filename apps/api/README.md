# ChronoLex API (`apps/api`)

FastAPI backend service powering the ChronoLex regulatory compliance assistant.

## Features (Current Phase)

- FastAPI service with structured modular architecture.
- Health check and project status verification endpoints.
- CORS configuration for local frontend communication.
- Graceful configuration management via environment variables with sensible defaults.

## Project Structure

```
apps/api/
├── app/
│   ├── main.py          # FastAPI application entrypoint
│   ├── api/             # Future API route handlers
│   ├── core/            # Configuration and settings (config.py)
│   ├── models/          # Future Pydantic request/response schemas
│   ├── services/        # Future RAG, retrieval, and embedding services
│   └── utils/           # Shared utility helpers
├── tests/
│   └── test_main.py     # API unit and integration tests
├── requirements.txt     # Python dependencies
└── README.md
```

## Local Development

### 1. Set Up Virtual Environment

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Verify Endpoints

- **Project Status**: [http://localhost:8000/](http://localhost:8000/)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Run Tests

```bash
pytest
```

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
cp ../../.env.example ../../.env
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
# From repository root
python scripts/demo_llm.py
```
If credentials are not yet set in `.env`, the script displays an informative message explaining how to configure credentials without crashing.

### Testing the Chat Completion Endpoint
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
pytest -v
```
