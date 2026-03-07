"""
WoxBot Configuration Module
Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field


# Project root: WoxBot/
BASE_DIR = Path(__file__).resolve().parent.parent


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
    log_level: str = Field(default="DEBUG")

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
