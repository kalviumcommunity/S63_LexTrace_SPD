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
