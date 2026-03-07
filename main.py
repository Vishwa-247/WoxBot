"""
WoxBot — Agentic RAG system for Woxsen University
Main FastAPI application entry-point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logger import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    settings = get_settings()
    logger.info("🚀 %s v%s starting in [%s] mode", settings.app_name, settings.app_version, settings.app_env)
    yield
    logger.info("🛑 %s shutting down", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Agentic RAG system for Woxsen University",
        lifespan=lifespan,
    )

    # ── CORS Middleware ──────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────
    app.include_router(health_router, prefix="/api", tags=["Health"])

    return app


app = create_app()
