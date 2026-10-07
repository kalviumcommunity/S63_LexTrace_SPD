from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Time-aware, source-grounded regulatory compliance RAG API.",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def get_root() -> dict[str, str]:
    """Root endpoint returning basic project status."""
    return {
        "project": "ChronoLex",
        "status": "running",
        "message": "ChronoLex API is initialized",
    }


@app.get("/health")
def get_health() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "ok",
    }
