"""
Tests for the ingestion pipeline — loader, chunking, embedder.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── Loader Tests ─────────────────────────────────────────────────────


class TestLoader:
    """Test PDF loading and scanned page detection."""

    def test_load_nonexistent_file(self):
        """Loader should raise FileNotFoundError for missing file."""
        from app.ingestion.loader import load_pdf

        with pytest.raises(FileNotFoundError):
            load_pdf("nonexistent_file.pdf")

    def test_load_non_pdf(self, tmp_path):
        """Loader should handle non-PDF files (PyMuPDF may open them)."""
        from app.ingestion.loader import PDFDocument, load_pdf

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("This is not a PDF")
        # PyMuPDF can open some non-PDF files; verify it returns a PDFDocument
        result = load_pdf(str(txt_file))
        assert isinstance(result, PDFDocument)


# ── Chunking Tests ───────────────────────────────────────────────────


class TestChunking:
    """Test section-based chunking."""

    def test_heading_detection(self):
        """Heading patterns should be detected correctly."""
        from app.ingestion.chunking import _is_heading

        assert _is_heading("CHAPTER 1: INTRODUCTION")
        assert _is_heading("1.1 Overview of Data Structures")
        assert _is_heading("Chapter 3: Sorting Algorithms")
        assert not _is_heading("this is a normal sentence about sorting.")
        assert not _is_heading("")

    def test_token_estimation(self):
        """Token estimation should be roughly accurate."""
        from app.ingestion.chunking import _estimate_tokens

        text = "Hello world this is a test sentence with some words."
        tokens = _estimate_tokens(text)
        # ~1 token per 4 chars, so ~51/4 ≈ 12-13
        assert 8 <= tokens <= 20

    def test_chunk_size_constraint(self):
        """Chunking should produce at least one chunk from a section."""
        from app.ingestion.chunking import Section, _split_section_into_chunks

        # Create a section with several lines
        lines = ["This is a test sentence number {}.".format(i) for i in range(100)]
        section = Section(title="Test Section", start_page=1, lines=lines)
        chunks = _split_section_into_chunks(section, "test.pdf", chunk_size=400, chunk_overlap=80)

        assert len(chunks) >= 1
        # All chunks should have text content
        for chunk in chunks:
            assert len(chunk.text) > 0
            assert chunk.filename == "test.pdf"


# ── Safe Calculator Tests ────────────────────────────────────────────


class TestCalculator:
    """Test the safe calculator (no eval)."""

    def test_average(self):
        from app.agent.tools import safe_calculate

        result = safe_calculate("average of 8.5, 9.0, 7.5, 8.0")
        assert "8.25" in result

    def test_cgpa(self):
        from app.agent.tools import safe_calculate

        result = safe_calculate("cgpa of 9, 8, 7, 8, 9")
        assert "8.2" in result

    def test_percentage(self):
        from app.agent.tools import safe_calculate

        result = safe_calculate("75% of 800")
        assert "600" in result

    def test_basic_arithmetic(self):
        from app.agent.tools import safe_calculate

        result = safe_calculate("25 + 75")
        assert "100" in result

    def test_division_by_zero(self):
        from app.agent.tools import safe_calculate

        result = safe_calculate("10 / 0")
        # Should handle gracefully, not crash
        assert isinstance(result, str)


# ── Router Tests ─────────────────────────────────────────────────────


class TestRouter:
    """Test keyword pre-router."""

    def test_document_qa_keywords(self):
        from app.agent.router import keyword_pre_route

        assert keyword_pre_route("what is in my uploaded pdf?") == "document_qa"
        assert keyword_pre_route("explain the syllabus") == "document_qa"
        assert keyword_pre_route("according to the document") == "document_qa"

    def test_calculation_keywords(self):
        from app.agent.router import keyword_pre_route

        assert keyword_pre_route("calculate my cgpa") == "calculation"
        assert keyword_pre_route("what is my gpa?") == "calculation"
        assert keyword_pre_route("percentage of 450 out of 500") == "calculation"

    def test_web_search_keywords(self):
        from app.agent.router import keyword_pre_route

        assert keyword_pre_route("latest news about AI") == "web_search"
        assert keyword_pre_route("trending topics in 2025") == "web_search"

    def test_summarize_keywords(self):
        from app.agent.router import keyword_pre_route

        assert keyword_pre_route("summarize chapter 3") == "summarize"
        assert keyword_pre_route("give me a tldr") == "summarize"

    def test_document_before_web(self):
        """Document keywords should take priority over web keywords."""
        from app.agent.router import keyword_pre_route

        # "shared right now" has "right now" which was in web_keywords before fix
        assert keyword_pre_route("analyze the document I shared") == "document_qa"

    def test_ambiguous_returns_none(self):
        from app.agent.router import keyword_pre_route

        result = keyword_pre_route("hello how are you")
        assert result is None


# ── Evaluation Metrics Tests ─────────────────────────────────────────


class TestMetrics:
    """Test RAGAS-style evaluation metrics."""

    def test_faithfulness_grounded(self):
        from app.evaluation.metrics import faithfulness

        answer = "Bubble sort compares adjacent elements and swaps them."
        context = ["Bubble sort works by comparing adjacent elements and swapping them if they are in wrong order."]
        score = faithfulness(answer, context)
        assert score > 0.5  # Should be high for grounded answer

    def test_faithfulness_hallucinated(self):
        from app.evaluation.metrics import faithfulness

        answer = "Quantum computing uses qubits to perform parallel calculations in superposition."
        context = ["Bubble sort compares adjacent elements."]
        score = faithfulness(answer, context)
        assert score < 0.5  # Should be low for unrelated answer

    def test_answer_relevancy(self):
        from app.evaluation.metrics import answer_relevancy

        score = answer_relevancy(
            "What is bubble sort?",
            "Bubble sort is a comparison-based sorting algorithm."
        )
        assert score > 0.3

    def test_hallucination_rate(self):
        from app.evaluation.metrics import hallucination_rate

        answer = "This text is supported by context."
        context = ["This text is supported by context."]
        rate = hallucination_rate(answer, context)
        assert rate < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
