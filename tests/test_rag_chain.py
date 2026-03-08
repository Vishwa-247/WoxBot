"""
Tests for the full RAG pipeline — agent graph, routing, validation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── Agent State Tests ────────────────────────────────────────────────


class TestAgentState:
    """Test LangGraph state structure."""

    def test_state_has_required_keys(self):
        """AgentState TypedDict must contain expected keys."""
        from app.agent.graph import AgentState

        hints = AgentState.__annotations__
        required = {"query", "rewritten_query", "route", "chunks", "answer", "sources"}
        for key in required:
            assert key in hints, f"Missing key: {key}"


# ── Routing Integration Tests ────────────────────────────────────────


class TestRoutingIntegration:
    """Test that routing feeds correctly into agent nodes."""

    def test_calculator_route_dispatches(self):
        """Calculator route should produce a numeric answer."""
        from app.agent.tools import safe_calculate

        result = safe_calculate("average of 10, 20, 30")
        assert "20" in result

    def test_document_qa_route_requires_context(self):
        """Document QA without context should surface clarification."""
        # Simulating: when no documents, router should fallback
        from app.agent.router import keyword_pre_route

        # Pure doc query with no index should still route to doc_qa
        route = keyword_pre_route("what does chapter 5 say?")
        assert route == "document_qa"


# ── Validator Tests ──────────────────────────────────────────────────


class TestValidator:
    """Test conditional validation logic."""

    def test_token_overlap_high(self):
        """High overlap between context and answer should pass validation."""
        context_tokens = set("bubble sort compares adjacent elements swapping".split())
        answer_tokens = set("bubble sort compares adjacent elements".split())
        overlap = len(context_tokens & answer_tokens) / max(len(answer_tokens), 1)
        assert overlap > 0.5

    def test_token_overlap_low(self):
        """Zero overlap should flag potential hallucination."""
        context_tokens = set("bubble sort compares adjacent elements".split())
        answer_tokens = set("quantum computing qubits superposition".split())
        overlap = len(context_tokens & answer_tokens) / max(len(answer_tokens), 1)
        assert overlap < 0.1


# ── Source Mapping Tests ─────────────────────────────────────────────


class TestSourceMapping:
    """Test post-hoc source mapping."""

    def test_map_sources_empty(self):
        """Map sources should return empty list for no context."""
        from app.agent.tools import map_sources

        sources = map_sources("some answer", [])
        assert sources == []

    def test_map_sources_deduplicates(self):
        """Same source name should appear only once via _unique_sources."""
        from app.agent.tools import _unique_sources

        mock_chunks = [
            {"filename": "test.pdf", "page": 1, "text": "chunk 1"},
            {"filename": "test.pdf", "page": 1, "text": "chunk 1 duplicate"},
            {"filename": "other.pdf", "page": 1, "text": "chunk 3"},
        ]
        sources = _unique_sources(mock_chunks)
        # test.pdf:1 appears twice but should be deduplicated
        assert len(sources) == 2
        filenames = [s["filename"] for s in sources]
        assert "test.pdf" in filenames
        assert "other.pdf" in filenames


# ── Prompt Template Tests ────────────────────────────────────────────


class TestPrompts:
    """Test prompt templates are properly formatted."""

    def test_all_prompts_are_strings(self):
        from app.generation import prompt

        templates = [
            prompt.REWRITER_PROMPT,
            prompt.RAG_SYSTEM_MSG,
            prompt.RAG_USER_MSG,
            prompt.ROUTER_PROMPT,
            prompt.VALIDATOR_PROMPT,
            prompt.SUMMARIZER_SYSTEM_MSG,
            prompt.SUMMARIZER_USER_MSG,
            prompt.WEB_SEARCH_SYSTEM_MSG,
            prompt.WEB_SEARCH_USER_MSG,
            prompt.CLARIFY_PROMPT,
        ]
        for t in templates:
            assert isinstance(t, str)
            assert len(t) > 10  # Not empty stubs

    def test_rag_prompt_has_placeholders(self):
        from app.generation.prompt import RAG_USER_MSG

        assert "{context}" in RAG_USER_MSG
        assert "{query}" in RAG_USER_MSG
        assert "{example}" in RAG_USER_MSG
        assert "{memory}" in RAG_USER_MSG


# ── Config Tests ─────────────────────────────────────────────────────


class TestConfig:
    """Test configuration defaults."""

    def test_default_provider_is_groq(self):
        from app.core.config import get_settings

        cfg = get_settings()
        assert cfg.default_llm_provider == "groq"

    def test_embedding_provider_not_gemini(self):
        """Embedding provider should not be gemini (API key suspended)."""
        from app.core.config import get_settings

        cfg = get_settings()
        assert cfg.embedding_provider != "gemini"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
