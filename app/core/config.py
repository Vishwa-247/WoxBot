"""
WoxBot Configuration Module
Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

# Project root: WoxBot/
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from .env file and environment variables."""

    # ── App ──────────────────────────────────────────────
    app_name: str = Field(default="WoxBot")
    app_version: str = Field(default="1.0.0")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)

    # ── Server ───────────────────────────────────────────
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # ── CORS ─────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173,http://localhost:8080")

    # ── Logging ──────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Gemini (Primary LLM + Embeddings) ────────────────
    gemini_api_key: str = Field(default="")

    # ── Multi-LLM Providers ──────────────────────────────
    grok_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    local_phi3_url: str = Field(default="http://localhost:11434")
    default_llm_provider: str = Field(default="groq")
    default_llm_model: str = Field(default="llama-3.1-8b-instant")

    # ── Ingestion / Chunking ─────────────────────────────
    chunk_size: int = Field(default=400)
    chunk_overlap: int = Field(default=80)
    embedding_provider: str = Field(default="openrouter")
    embedding_model_version: str = Field(default="text-embedding-3-small")

    # ── Retrieval ────────────────────────────────────────
    retrieval_top_k: int = Field(default=20)
    rerank_top_k: int = Field(default=8)
    similarity_threshold: str = Field(default="calibrate_from_data")

    # ── API Auth ─────────────────────────────────────────
    api_key: str = Field(default="woxbot-dev-key")

    # ── Agent / Memory ───────────────────────────────────
    max_memory_turns: int = Field(default=5)

    # ── MongoDB (conversation memory persistence) ────────────────────
    mongodb_uri: str = Field(default="")
    mongodb_db: str = Field(default="woxbot")

    # ── Paths ────────────────────────────────────────────
    vector_db_path: str = Field(default="./vector_db")
    data_raw_path: str = Field(default="./data/raw")

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton for application settings."""
    return Settings()
