import os
from pathlib import Path
from dotenv import load_dotenv

# Load root .env or local .env if available
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()


class Settings:
    PROJECT_NAME: str = "ChronoLex"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS configuration
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]

    # LLM API Configuration
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: str = os.getenv(
        "OPENAI_BASE_URL", "https://api.openai.com/v1"
    )
    CHAT_MODEL: str = os.getenv("CHAT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    OPENAI_MODEL: str = CHAT_MODEL
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "text-embedding-3-small"
    )

    # Planned Vector Database Configuration
    VECTOR_DB_URL: str = os.getenv("VECTOR_DB_URL", "http://localhost:8000")
    VECTOR_DB_COLLECTION: str = os.getenv(
        "VECTOR_DB_COLLECTION", "chronolex_regulations"
    )

    def validate_llm_config(self) -> None:
        """Validate that required LLM configuration is present."""
        if not self.OPENAI_API_KEY or not self.OPENAI_API_KEY.strip():
            raise ValueError(
                "OPENAI_API_KEY is not configured. Please set OPENAI_API_KEY in your environment or .env file."
            )


settings = Settings()
