"""
Agent Nodes — All LangGraph node functions.

Node flow (per build plan):
  START → Query Rewriter → Keyword Pre-Router → LangGraph Router
    ├── document_qa  → RAG Node → Hybrid Retrieval → Reranker(8) → LLM → Source Map
    ├── web_search   → Search Node → DuckDuckGo → LLM
    ├── calculation  → Calculator Node → pure float arithmetic
    ├── summarize    → Summarizer Node → chunks → LLM
    └── unclear      → Clarify Node → ask user to rephrase
  → Validator (borderline only) → Memory → END
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent import mongo_memory as memory
from app.agent import router
from app.agent.tools import (format_search_results, map_sources,
                             safe_calculate, web_search)
from app.generation import llm
from app.generation.prompt import (CLARIFY_PROMPT, FORMATTING_EXAMPLE,
                                   RAG_SYSTEM_MSG, RAG_USER_MSG,
                                   REWRITER_PROMPT, STUDY_PLAN_PROMPT,
                                   SUMMARIZER_SYSTEM_MSG, SUMMARIZER_USER_MSG,
                                   WEB_SEARCH_SYSTEM_MSG, WEB_SEARCH_USER_MSG)
from app.generation.validator import validate
from app.retrieval.reranker import rerank
from app.retrieval.retriever import hybrid_retrieve

logger = logging.getLogger("woxbot")


# ── Type alias for the shared state ─────────────────────────────────
# AgentState is a TypedDict defined in graph.py; nodes receive/return dicts.


def rewriter_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Query Rewriter — FIRST NODE (Constraint #3).

    Rewrites vague follow-up questions into standalone queries
    using conversation history.
    """
    query = state["query"]
    session_id = state.get("session_id", "default")
    history = memory.get_history(session_id)

    # If no history, query is already standalone
    if history == "(No prior conversation)":
        logger.info("Rewriter: no history, query unchanged.")
        return {"rewritten_query": query}

    prompt = REWRITER_PROMPT.format(history=history, query=query)
    rewritten = llm.generate(
        prompt,
        provider=state.get("provider"),
        model=state.get("model"),
        temperature=0.0,
    ).strip()

    # Guard: if rewriter returns empty, use original
    if not rewritten:
        rewritten = query

    logger.info("Rewriter: '%s' → '%s'", query, rewritten)
    return {"rewritten_query": rewritten}


def router_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Router — Keyword pre-router + LLM router fallback.

    Sets the 'route' field which determines which processing node runs.
    """
    query = state.get("rewritten_query", state["query"])
    route = router.route(
        query,
        provider=state.get("provider"),
        model=state.get("model"),
    )
    logger.info("Router: query='%s' → route='%s'", query, route)
    return {"route": route}


def rag_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    RAG Node — Hybrid Retrieval → Reranker(8) → LLM → Source Map.

    Full document QA pipeline with anti-hallucination prompt.
    """
    query = state.get("rewritten_query", state["query"])

    # Step 1: Hybrid retrieval (FAISS + BM25 → RRF)
    candidates = hybrid_retrieve(query)
    logger.info("RAG: %d candidates from hybrid retrieval.", len(candidates))

    # Step 2: Rerank → top 8 (Constraint #2)
    top_chunks = rerank(query, candidates)
    logger.info("RAG: %d chunks after reranking.", len(top_chunks))

    if not top_chunks:
        return {
            "answer": "I don't have enough information in the uploaded documents to answer this.",
            "sources": [],
            "chunks": [],
        }

    # Step 3: Build context from top chunks
    context = "\n\n---\n\n".join(
        f"[{c.get('section_title', 'N/A')}]\n{c.get('text', '')}"
        for c in top_chunks
    )

    # Step 4: Generate answer with anti-hallucination prompt
    session_id = state.get("session_id", "default")
    history_text = memory.get_history(session_id)
    messages = [
        {"role": "system", "content": RAG_SYSTEM_MSG},
        {"role": "user", "content": RAG_USER_MSG.format(
            example=FORMATTING_EXAMPLE, context=context,
            memory=history_text, query=query)},
    ]
    answer = llm.generate(
        "",
        provider=state.get("provider"),
        model=state.get("model"),
        messages=messages,
    )

    # Step 5: Post-hoc source mapping (Fix 3 — NEVER inline citations)
    sources = map_sources(answer, top_chunks)

    logger.info("RAG: generated answer (%d chars), %d sources.", len(answer), len(sources))
    return {"answer": answer, "sources": sources, "chunks": top_chunks}


def search_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Web Search Node — DuckDuckGo → LLM synthesis.
    """
    query = state.get("rewritten_query", state["query"])

    # Step 1: Web search
    results = web_search(query)
    formatted = format_search_results(results)

    if not results:
        return {
            "answer": "I couldn't find relevant web search results. Please try rephrasing your query.",
            "sources": [],
            "chunks": [],
        }

    # Step 2: LLM synthesis
    messages = [
        {"role": "system", "content": WEB_SEARCH_SYSTEM_MSG},
        {"role": "user", "content": WEB_SEARCH_USER_MSG.format(search_results=formatted, query=query)},
    ]
    answer = llm.generate(
        "",
        provider=state.get("provider"),
        model=state.get("model"),
        messages=messages,
    )

    # Web sources
    sources = [
        {"title": r["title"], "url": r["href"], "snippet": r["body"][:200]}
        for r in results
    ]

    logger.info("Search: generated answer from %d web results.", len(results))
    return {"answer": answer, "sources": sources, "chunks": []}


def calc_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Calculator Node — Pure float arithmetic (NO eval() — Constraint #4).
    """
    query = state.get("rewritten_query", state["query"])
    result = safe_calculate(query)
    logger.info("Calculator: '%s' → '%s'", query, result)
    return {"answer": result, "sources": [], "chunks": []}


def summarizer_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Summarizer Node — Retrieve all relevant chunks and summarize.
    """
    query = state.get("rewritten_query", state["query"])

    # Retrieve more chunks for summarization
    candidates = hybrid_retrieve(query, top_k=30)
    top_chunks = rerank(query, candidates, top_k=8)

    if not top_chunks:
        return {
            "answer": "I don't have enough document content to summarize. Please upload relevant documents first.",
            "sources": [],
            "chunks": [],
        }

    content = "\n\n---\n\n".join(c.get("text", "") for c in top_chunks)
    messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM_MSG},
        {"role": "user", "content": SUMMARIZER_USER_MSG.format(content=content)},
    ]
    answer = llm.generate(
        "",
        provider=state.get("provider"),
        model=state.get("model"),
        messages=messages,
    )

    sources = map_sources(answer, top_chunks)
    logger.info("Summarizer: generated summary from %d chunks.", len(top_chunks))
    return {"answer": answer, "sources": sources, "chunks": top_chunks}


def clarify_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Clarify Node — Ask ONE specific clarifying question.
    Includes available document list for context-aware clarification.
    """
    query = state.get("rewritten_query", state["query"])
    doc_list = state.get("available_docs", "No documents uploaded yet")
    if isinstance(doc_list, list):
        doc_list = ", ".join(doc_list) if doc_list else "No documents uploaded yet"
    prompt = CLARIFY_PROMPT.format(query=query, doc_list=doc_list)
    answer = llm.generate(
        prompt,
        provider=state.get("provider"),
        model=state.get("model"),
    )
    logger.info("Clarify: asking user to rephrase.")
    return {"answer": answer, "sources": [], "chunks": []}


def study_planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Study Planner Node — builds a structured study plan from uploaded docs.
    """
    query = state.get("rewritten_query", state["query"])
    doc_summaries = state.get("doc_summaries", "No document summaries available.")
    if isinstance(doc_summaries, list):
        doc_summaries = "\n\n".join(
            f"**{s.get('filename', 'Unknown')}**:\n{s.get('summary', 'No summary')}"
            for s in doc_summaries
        ) if doc_summaries else "No document summaries available."

    prompt = STUDY_PLAN_PROMPT.format(query=query, doc_summaries=doc_summaries)
    answer = llm.generate(
        prompt,
        provider=state.get("provider"),
        model=state.get("model"),
    )
    logger.info("Study Planner: generated plan for query='%s'", query)
    return {"answer": answer, "sources": [], "chunks": []}


def validator_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Validator Node — Conditional validation (Fix 4).

    Only runs for document_qa and summarize routes.
    Skips for web_search, calculation, and unclear.
    """
    route = state.get("route", "")
    answer = state.get("answer", "")
    chunks = state.get("chunks", [])

    # Only validate RAG-based answers
    if route not in ("document_qa", "summarize") or not chunks:
        logger.info("Validator: skipping for route='%s'.", route)
        return {"validation": {"grounded": True, "method": "skipped"}}

    query = state.get("rewritten_query", state["query"])
    result = validate(
        query=query,
        answer=answer,
        chunks=chunks,
        provider=state.get("provider"),
        model=state.get("model"),
    )

    logger.info(
        "Validator: grounded=%s, confidence=%s, method=%s",
        result["grounded"],
        result["confidence"],
        result["method"],
    )

    # If ungrounded, append a disclaimer
    if not result["grounded"]:
        disclaimer = "\n\n⚠️ *Note: This answer may not be fully supported by the uploaded documents. Please verify the information.*"
        return {
            "answer": answer + disclaimer,
            "validation": result,
        }

    return {"validation": result}


def memory_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Memory Node — Save the turn to conversation buffer.
    """
    session_id = state.get("session_id", "default")
    query = state["query"]
    answer = state.get("answer", "")

    memory.save_turn(session_id, query, answer)
    return {}
