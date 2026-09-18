"""
Enterprise Multi-Agent Platform — Centralized Configuration

Uses Pydantic Settings to load configuration from environment variables
and .env files. All service configurations are centralized here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ──────────────────────────────────────────────────────────────
# Base paths
# ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"


class Settings(BaseSettings):
    """Centralized application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o", description="Primary LLM model")
    llm_fallback_model: str = Field(default="gpt-4o-mini", description="Fallback LLM model")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4096, ge=1)

    # ── Embedding ─────────────────────────────────────────────
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536)

    # ── Qdrant Vector Store ───────────────────────────────────
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str = Field(default="")
    qdrant_collection_name: str = Field(default="enterprise_docs")

    # ── Redis Cache ───────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_ttl_seconds: int = Field(default=3600)

    # ── Database ──────────────────────────────────────────────
    database_url: str = Field(default=f"sqlite+aiosqlite:///{DATA_DIR / 'enterprise.db'}")

    # ── MLflow ────────────────────────────────────────────────
    mlflow_tracking_uri: str = Field(default="http://localhost:5000")
    mlflow_experiment_name: str = Field(default="enterprise-agent-platform")

    # ── FastAPI ───────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=1)
    api_cors_origins: list[str] = Field(
        default=["http://localhost:8501", "http://localhost:3000"]
    )

    # ── Streamlit ─────────────────────────────────────────────
    streamlit_port: int = Field(default=8501)
    streamlit_backend_url: str = Field(default="http://localhost:8000")

    # ── Logging ───────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # ── Security ──────────────────────────────────────────────
    api_key: str = Field(default="")
    rate_limit_rpm: int = Field(default=60)

    # ── Validators ────────────────────────────────────────────
    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # ── Computed Paths ────────────────────────────────────────
    @property
    def data_dir(self) -> Path:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR

    @property
    def upload_dir(self) -> Path:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return UPLOAD_DIR

    @property
    def sqlite_path(self) -> Path:
        """Extract raw SQLite file path from the database URL."""
        path_str = self.database_url.replace("sqlite+aiosqlite:///", "")
        return Path(path_str)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
