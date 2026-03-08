"""
MongoDB Connection — Async motor client with singleton pattern.

Provides:
  - connect_db() — call at startup via lifespan()
  - get_db() — returns the woxbot database
  - close_db() — call at shutdown
"""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger("woxbot")

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    """Initialize the MongoDB connection. Call once at startup."""
    global _client
    settings = get_settings()
    uri = settings.mongodb_uri
    if not uri:
        logger.warning("[MongoDB] MONGODB_URI not set — MongoDB features disabled.")
        return

    _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    # Verify connectivity
    try:
        await _client.admin.command("ping")
        logger.info("[MongoDB] Connected to %s", uri.split("@")[-1] if "@" in uri else uri)
    except Exception as e:
        logger.error("[MongoDB] Connection failed: %s", e)
        _client = None


def get_db() -> AsyncIOMotorDatabase | None:
    """Return the woxbot database. Returns None if not connected."""
    if _client is None:
        return None
    settings = get_settings()
    return _client[settings.mongodb_db]


async def close_db() -> None:
    """Close the MongoDB connection. Call at shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("[MongoDB] Connection closed.")
