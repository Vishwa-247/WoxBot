"""
Conversation Memory — Last N turns buffer.

Stores per-session conversation history for query rewriting.
MAX_MEMORY_TURNS from config (default 5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.core.config import get_settings

logger = logging.getLogger("woxbot")


@dataclass
class Turn:
    """A single conversation turn."""
    query: str
    answer: str


@dataclass
class ConversationBuffer:
    """Rolling buffer of the last N conversation turns."""
    max_turns: int = 5
    turns: list[Turn] = field(default_factory=list)

    def add(self, query: str, answer: str) -> None:
        """Add a turn, dropping oldest if at capacity."""
        self.turns.append(Turn(query=query, answer=answer))
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns :]

    def format_history(self) -> str:
        """Format conversation history for prompt injection."""
        if not self.turns:
            return "(No prior conversation)"
        lines: list[str] = []
        for t in self.turns:
            lines.append(f"User: {t.query}")
            lines.append(f"Assistant: {t.answer}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all turns."""
        self.turns.clear()


# ── Session Store ────────────────────────────────────────────────────
# In-memory dict mapping session_id → ConversationBuffer
# For production, swap with Redis or DB-backed store.

_sessions: dict[str, ConversationBuffer] = {}


def get_buffer(session_id: str) -> ConversationBuffer:
    """Get or create a conversation buffer for the given session."""
    if session_id not in _sessions:
        settings = get_settings()
        _sessions[session_id] = ConversationBuffer(max_turns=settings.max_memory_turns)
        logger.info("Created new conversation buffer for session: %s", session_id)
    return _sessions[session_id]


def save_turn(session_id: str, query: str, answer: str) -> None:
    """Save a conversation turn to the session buffer."""
    buf = get_buffer(session_id)
    buf.add(query, answer)
    logger.debug(
        "Saved turn for session %s (now %d turns).",
        session_id,
        len(buf.turns),
    )


def get_history(session_id: str) -> str:
    """Get formatted conversation history for the session."""
    return get_buffer(session_id).format_history()


def clear_session(session_id: str) -> None:
    """Clear conversation history for a session."""
    if session_id in _sessions:
        _sessions[session_id].clear()
        logger.info("Cleared conversation buffer for session: %s", session_id)
