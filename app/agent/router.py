"""
Router — Keyword pre-router + LLM router for ambiguous queries.

Pipeline (per build plan Fix 2):
  1. Keyword pre-router: handles 90% of cases deterministically
  2. LLM router: only called for ambiguous queries that don't match keywords
  3. Index-aware fallback: defaults to document_qa when docs are indexed

Routes:
  - document_qa: uploaded docs, syllabus, course content
  - web_search: current events, latest news, real-time info
  - calculation: CGPA, GPA, percentages, math
  - summarize: summarize documents or topics
  - unclear: vague queries needing clarification
"""

from __future__ import annotations

import logging

from app.generation.llm import generate
from app.generation.prompt import ROUTER_PROMPT
from app.retrieval.vector_store import has_documents

logger = logging.getLogger("woxbot")

# Valid route names
VALID_ROUTES = {"document_qa", "web_search", "calculation", "summarize", "unclear", "study_planner"}


def keyword_pre_route(query: str) -> str | None:
    """
    Rule-based routing BEFORE hitting the LLM router.
    Handles 90% of cases deterministically.

    Priority: calculation → summarize → document_qa → web_search.
    document_qa is checked BEFORE web_search to avoid false positives
    from phrases like "right now" in document-related queries.

    Returns:
        Route name if matched, None if ambiguous (→ pass to LLM router).
    """
    q = query.lower()

    # Document QA keywords (broad — covers uploaded files, named docs, university context)
    doc_keywords = [
        "my notes", "uploaded", "syllabus", "lab manual", "my pdf",
        "my document", "course content", "lecture", "chapter",
        "unit", "module", "assignment", "exam pattern", "curriculum",
        "university", "woxsen", "college", "campus", "department",
        "professor", "faculty", "semester", "academic",
        "document", "the file", "the pdf", "shared", "attached",
        "analyze the", "read the", "from the", "in the pdf",
        "in the document", "in the file", "what does the",
        "according to", "based on the", "refer to",
        "i gave", "i sent", "i provided", "i shared",
    ]

    # Calculation keywords
    calc_keywords = [
        "cgpa", "gpa", "marks", "average", "calculate", "percentage",
        "grade point", "total marks", "score", "compute", "add up",
    ]

    # Web search keywords
    web_keywords = [
        "latest", "current", "news", "today", "recent",
        "2024", "2025", "2026", "trending",
        "update", "announce", "launch",
    ]

    # Summarize keywords
    summarize_keywords = [
        "summarize", "summary", "overview", "brief",
        "key points", "main points", "tldr", "tl;dr",
    ]

    # Study planner keywords
    study_keywords = [
        "exam", "study plan", "prepare", "revision", "help me study",
        "tomorrow exam", "last minute", "important topics", "what to study",
        "study guide", "exam prep", "review for", "study schedule",
    ]

    if any(k in q for k in calc_keywords):
        logger.info("Keyword pre-router → calculation")
        return "calculation"

    if any(k in q for k in study_keywords):
        logger.info("Keyword pre-router → study_planner")
        return "study_planner"

    if any(k in q for k in summarize_keywords):
        logger.info("Keyword pre-router → summarize")
        return "summarize"

    # Document QA checked BEFORE web_search
    if any(k in q for k in doc_keywords):
        logger.info("Keyword pre-router → document_qa")
        return "document_qa"

    if any(k in q for k in web_keywords):
        logger.info("Keyword pre-router → web_search")
        return "web_search"

    return None  # Ambiguous → pass to LLM router


def llm_route(query: str, provider: str | None = None, model: str | None = None) -> str:
    """
    LLM-based routing for ambiguous queries.

    Args:
        query: The standalone (rewritten) query.
        provider: Override LLM provider.
        model: Override LLM model.

    Returns:
        One of the VALID_ROUTES.
    """
    prompt = ROUTER_PROMPT.format(query=query)
    kwargs: dict = {}
    if provider:
        kwargs["provider"] = provider
    if model:
        kwargs["model"] = model

    result = generate(prompt, temperature=0.0, **kwargs).strip().lower()
    logger.info("LLM router result: '%s'", result)

    # Validate — fall back to document_qa if response is unexpected
    if result in VALID_ROUTES:
        return result

    # Try to extract a valid route from the response
    for route in VALID_ROUTES:
        if route in result:
            logger.info("Extracted route '%s' from LLM response.", route)
            return route

    logger.warning("LLM router returned unknown route '%s', defaulting to document_qa.", result)
    return "document_qa"


def route(query: str, provider: str | None = None, model: str | None = None) -> str:
    """
    Combined router: keyword pre-router → LLM router fallback → index-aware default.

    Args:
        query: The standalone (rewritten) query.
        provider: Override LLM provider.
        model: Override LLM model.

    Returns:
        Route name string.
    """
    # Step 1: Keyword pre-router (fast, deterministic)
    pre_route = keyword_pre_route(query)
    if pre_route is not None:
        return pre_route

    # Step 2: If documents are indexed and no keyword matched,
    # default to document_qa instead of calling LLM router.
    # This prevents generic questions about uploaded docs from going to web_search.
    if has_documents():
        logger.info("No keyword match but documents are indexed → document_qa")
        return "document_qa"

    # Step 3: LLM router for ambiguous queries (only when no docs indexed)
    logger.info("Query not matched by keyword pre-router, using LLM router.")
    return llm_route(query, provider=provider, model=model)
