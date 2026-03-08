"""
WoxBot — Agentic RAG system for Woxsen University
Main FastAPI application entry-point.
"""

from __future__ import annotations

import hmac
from contextlib import asynccontextmanager

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.sources import router as sources_router
from app.core.config import get_settings
from app.core.logger import logger
from app.db.chunk_store import ensure_indexes
from app.db.mongo import close_db, connect_db
from app.retrieval.reranker import _get_cross_encoder
from app.retrieval.vector_store import load_index
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

# ── API Key Auth ─────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)):
    """Validate X-API-Key header against configured key."""
    settings = get_settings()
    if not api_key or not hmac.compare_digest(api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook — preload models and connect DB."""
    settings = get_settings()
    logger.info("🚀 %s v%s starting in [%s] mode", settings.app_name, settings.app_version, settings.app_env)

    # ── MongoDB ──────────────────────────────────────────
    await connect_db()
    await ensure_indexes()
    logger.info("✅ MongoDB connected and indexes ensured.")

    # ── CrossEncoder reranker ────────────────────────────
    try:
        _get_cross_encoder()
        logger.info("✅ CrossEncoder model preloaded.")
    except Exception as e:
        logger.warning("⚠️ CrossEncoder preload failed: %s", e)

    # ── FAISS index ──────────────────────────────────────
    try:
        result = load_index()
        if result:
            logger.info("✅ FAISS index preloaded (%d vectors).", result[0].ntotal)
        else:
            logger.info("ℹ️ No FAISS index found — will be built on first ingest.")
    except Exception as e:
        logger.warning("⚠️ FAISS preload failed: %s", e)

    yield

    # ── Shutdown ─────────────────────────────────────────
    await close_db()
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
    # Health — no auth required
    app.include_router(health_router, prefix="/api", tags=["Health"])

    # Protected routes — require X-API-Key header
    app.include_router(
        chat_router,
        prefix="/api",
        tags=["Chat"],
        dependencies=[Depends(verify_api_key)],
    )
    app.include_router(
        ingest_router,
        prefix="/api",
        tags=["Ingest"],
        dependencies=[Depends(verify_api_key)],
    )
    app.include_router(
        sources_router,
        prefix="/api",
        tags=["Sources"],
        dependencies=[Depends(verify_api_key)],
    )

    return app


app = create_app()
