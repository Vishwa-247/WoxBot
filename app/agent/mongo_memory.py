"""
MongoDB-Backed Conversation Memory

Persists conversation turns to MongoDB so history survives server restarts.
Falls back to in-memory storage if MongoDB is unavailable.

Collection: woxbot.conversations
Document schema:
  {
    session_id: str,
    turns: [{ query, answer, ts }],
    updated_at: datetime
  }
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import get_settings

logger = logging.getLogger("woxbot")

# ── Lazy client — connected on first use ────────────────────────────
_client = None
_collection = None


def _get_collection():
    """Return the MongoDB collection, initialising the client on first call."""
    global _client, _collection
    if _collection is not None:
        return _collection

    settings = get_settings()
    uri = getattr(settings, "mongodb_uri", None)
    if not uri:
        logger.warning("MONGODB_URI not set — conversation memory will not be persisted.")
        return None

    try:
        from pymongo import MongoClient
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        # Ping to verify connection
        _client.admin.command("ping")
        db = _client["woxbot"]
        _collection = db["conversations"]
        # Index on session_id for fast lookups
        _collection.create_index("session_id", unique=True)
        logger.info("MongoDB conversation memory connected.")
        return _collection
    except Exception as e:
        logger.warning("MongoDB connection failed (%s) — falling back to in-memory memory.", e)
        return None


# ── In-memory fallback ───────────────────────────────────────────────
_fallback: dict[str, list[dict]] = {}


def _fallback_save(session_id: str, query: str, answer: str, max_turns: int) -> None:
    turns = _fallback.setdefault(session_id, [])
    turns.append({"query": query, "answer": answer})
    if len(turns) > max_turns:
        _fallback[session_id] = turns[-max_turns:]


def _fallback_get(session_id: str) -> list[dict]:
    return _fallback.get(session_id, [])


def _fallback_clear(session_id: str) -> None:
    _fallback.pop(session_id, None)


# ── Public API ───────────────────────────────────────────────────────

def save_turn(session_id: str, query: str, answer: str) -> None:
    """Append a conversation turn to MongoDB (or in-memory fallback)."""
    settings = get_settings()
    max_turns = settings.max_memory_turns
    col = _get_collection()

    if col is None:
        _fallback_save(session_id, query, answer, max_turns)
        return

    try:
        # Fetch current turns, append, trim, upsert
        doc = col.find_one({"session_id": session_id}) or {"session_id": session_id, "turns": []}
        turns: list[dict] = doc.get("turns", [])
        turns.append({"query": query, "answer": answer, "ts": datetime.now(timezone.utc).isoformat()})
        if len(turns) > max_turns:
            turns = turns[-max_turns:]
        col.update_one(
            {"session_id": session_id},
            {"$set": {"turns": turns, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception as e:
        logger.warning("MongoDB save_turn error: %s — using fallback.", e)
        _fallback_save(session_id, query, answer, max_turns)


def get_history(session_id: str) -> str:
    """Return formatted conversation history for prompt injection."""
    col = _get_collection()

    if col is None:
        turns = _fallback_get(session_id)
    else:
        try:
            doc = col.find_one({"session_id": session_id})
            turns = doc.get("turns", []) if doc else []
        except Exception as e:
            logger.warning("MongoDB get_history error: %s — using fallback.", e)
            turns = _fallback_get(session_id)

    if not turns:
        return "(No prior conversation)"

    lines: list[str] = []
    for t in turns:
        lines.append(f"User: {t['query']}")
        lines.append(f"Assistant: {t['answer']}")
    return "\n".join(lines)


def clear_session(session_id: str) -> None:
    """Delete all conversation history for a session."""
    col = _get_collection()

    if col is None:
        _fallback_clear(session_id)
        return

    try:
        col.delete_one({"session_id": session_id})
    except Exception as e:
        logger.warning("MongoDB clear_session error: %s — using fallback.", e)
        _fallback_clear(session_id)
