"""
Agent Graph — LangGraph StateGraph definition.

Wires all nodes and edges for the WoxBot agent pipeline:
  START → rewriter → router → {rag|search|calc|summarize|clarify} → validator → memory → END

Constraint #3: Query Rewriter is the FIRST node.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.nodes import (calc_node, clarify_node, memory_node, rag_node,
                             rewriter_node, router_node, search_node,
                             summarizer_node, validator_node)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

logger = logging.getLogger("woxbot")


# ── Agent State ──────────────────────────────────────────────────────


class AgentState(TypedDict, total=False):
    """Shared state passed through all nodes in the graph."""
    # Input
    query: str
    session_id: str
    provider: str | None
    model: str | None

    # Set by rewriter
    rewritten_query: str

    # Set by router
    route: str

    # Set by processing nodes
    answer: str
    sources: list[dict]
    chunks: list[dict]

    # Set by validator
    validation: dict


# ── Route Dispatcher ─────────────────────────────────────────────────


def _route_dispatch(state: AgentState) -> str:
    """
    Conditional edge function — dispatches to the correct processing node
    based on the 'route' field set by router_node.
    """
    route = state.get("route", "document_qa")
    logger.info("Dispatching to route: %s", route)
    return route


# ── Build Graph ──────────────────────────────────────────────────────


def build_graph() -> StateGraph:
    """
    Build and compile the LangGraph agent.

    Returns:
        Compiled StateGraph ready to invoke.
    """
    graph = StateGraph(AgentState)

    # ── Add Nodes ────────────────────────────────────────
    graph.add_node("rewriter", rewriter_node)
    graph.add_node("router", router_node)
    graph.add_node("document_qa", rag_node)
    graph.add_node("web_search", search_node)
    graph.add_node("calculation", calc_node)
    graph.add_node("summarize", summarizer_node)
    graph.add_node("unclear", clarify_node)
    graph.add_node("validator", validator_node)
    graph.add_node("memory", memory_node)

    # ── Add Edges ────────────────────────────────────────

    # START → rewriter (Constraint #3: FIRST node)
    graph.add_edge(START, "rewriter")

    # rewriter → router
    graph.add_edge("rewriter", "router")

    # router → conditional dispatch to processing nodes
    graph.add_conditional_edges(
        "router",
        _route_dispatch,
        {
            "document_qa": "document_qa",
            "web_search": "web_search",
            "calculation": "calculation",
            "summarize": "summarize",
            "unclear": "unclear",
        },
    )

    # All processing nodes → validator
    graph.add_edge("document_qa", "validator")
    graph.add_edge("web_search", "validator")
    graph.add_edge("calculation", "validator")
    graph.add_edge("summarize", "validator")
    graph.add_edge("unclear", "validator")

    # validator → memory → END
    graph.add_edge("validator", "memory")
    graph.add_edge("memory", END)

    return graph.compile()


# ── Module-level compiled graph (singleton) ──────────────────────────

_compiled_graph = None


def get_graph():
    """Get the compiled graph (lazy singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        logger.info("Building LangGraph agent...")
        _compiled_graph = build_graph()
        logger.info("LangGraph agent built successfully.")
    return _compiled_graph


# ── Public API ───────────────────────────────────────────────────────


def run_agent(
    query: str,
    session_id: str = "default",
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Run the full agent pipeline synchronously.

    Args:
        query: User's question.
        session_id: Conversation session ID.
        provider: Override LLM provider (gemini, groq, openrouter, local).
        model: Override LLM model.

    Returns:
        Final agent state dict with answer, sources, validation, etc.
    """
    graph = get_graph()
    initial_state: AgentState = {
        "query": query,
        "session_id": session_id,
        "provider": provider,
        "model": model,
    }

    logger.info("Running agent: query='%s', session='%s', provider=%s", query, session_id, provider)
    result = graph.invoke(initial_state)
    logger.info("Agent completed: route=%s, answer_len=%d", result.get("route"), len(result.get("answer", "")))
    return result
