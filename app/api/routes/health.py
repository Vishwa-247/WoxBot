"""
WoxBot Health-check route.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import get_settings
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Lightweight liveness / readiness probe."""
    settings = get_settings()
    return {
        "status": "ok",
        "version": "1.0",
        "app": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
