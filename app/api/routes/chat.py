"""
Chat Route — POST /api/chat with SSE streaming.

SSE pattern (per build plan):
  1. Send raw text tokens one by one
  2. Send [SOURCES_START] marker
  3. Send JSON with sources
  4. Send [DONE] marker

Does NOT send each token as JSON — per build plan ❌ Do NOT rule.
"""

from __future__ import annotations

import json
import logging

from app.agent import memory
from app.agent import router as agent_router
from app.agent.graph import run_agent
from app.agent.tools import (format_search_results, map_sources,
                             safe_calculate, web_search)
from app.api.schemas import ChatRequest, ChatResponse
from app.generation import llm
from app.generation.prompt import (CLARIFY_PROMPT, RAG_SYSTEM_PROMPT,
                                   SUMMARIZER_PROMPT, WEB_SEARCH_PROMPT)
from app.generation.validator import validate
from app.retrieval.reranker import rerank
from app.retrieval.retriever import hybrid_retrieve
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

logger = logging.getLogger("woxbot")

router = APIRouter()


async def _generate_stream(
    query: str,
    session_id: str,
    provider: str | None,
    model: str | None,
):
    """
    SSE generator — runs the agent pipeline with streaming LLM output.

    Flow: rewrite → route → retrieve/process → stream tokens → send sources → [DONE]
    """
    # Step 1: Rewrite query (uses conversation history)
    history = memory.get_history(session_id)
    if history != "(No prior conversation)":
        from app.generation.prompt import REWRITER_PROMPT
        rewrite_prompt = REWRITER_PROMPT.format(history=history, query=query)
        rewritten = llm.generate(rewrite_prompt, provider=provider, model=model, temperature=0.0).strip()
        if rewritten:
            query = rewritten

    # Step 2: Route
    route = agent_router.route(query, provider=provider, model=model)
    logger.info("SSE stream: route=%s, query=%s", route, query)

    sources = []
    chunks = []
    answer_text = ""

    if route == "calculation":
        # Calculator — no streaming needed, instant result
        result = safe_calculate(query)
        yield f"data: {result}\n\n"
        answer_text = result

    elif route == "unclear":
        # Clarify — stream the clarification
        prompt = CLARIFY_PROMPT.format(query=query)
        async for token in llm.stream(prompt, provider=provider, model=model):
            yield f"data: {token}\n\n"
            answer_text += token

    elif route == "web_search":
        # Web search — get results, then stream synthesis
        results = web_search(query)
        formatted = format_search_results(results)
        if not results:
            msg = "I couldn't find relevant web search results. Please try rephrasing your query."
            yield f"data: {msg}\n\n"
            answer_text = msg
        else:
            prompt = WEB_SEARCH_PROMPT.format(search_results=formatted, query=query)
            async for token in llm.stream(prompt, provider=provider, model=model):
                yield f"data: {token}\n\n"
                answer_text += token
            sources = [
                {"title": r["title"], "url": r["href"], "snippet": r["body"][:200]}
                for r in results
            ]

    elif route == "summarize":
        # Summarize — retrieve chunks, then stream
        candidates = hybrid_retrieve(query, top_k=30)
        chunks = rerank(query, candidates, top_k=8)
        if not chunks:
            msg = "I don't have enough document content to summarize."
            yield f"data: {msg}\n\n"
            answer_text = msg
        else:
            content = "\n\n---\n\n".join(c.get("text", "") for c in chunks)
            prompt = SUMMARIZER_PROMPT.format(content=content)
            async for token in llm.stream(prompt, provider=provider, model=model):
                yield f"data: {token}\n\n"
                answer_text += token

    else:
        # document_qa (default) — full RAG pipeline with streaming
        candidates = hybrid_retrieve(query)
        chunks = rerank(query, candidates)
        if not chunks:
            msg = "I don't have enough information in the uploaded documents to answer this."
            yield f"data: {msg}\n\n"
            answer_text = msg
        else:
            context = "\n\n---\n\n".join(
                f"[{c.get('section_title', 'N/A')}]\n{c.get('text', '')}"
                for c in chunks
            )
            prompt = RAG_SYSTEM_PROMPT.format(context=context, query=query)
            async for token in llm.stream(prompt, provider=provider, model=model):
                yield f"data: {token}\n\n"
                answer_text += token

    # Post-hoc source mapping for RAG-based routes
    if route in ("document_qa", "summarize") and chunks and answer_text:
        sources = map_sources(answer_text, chunks)

        # Conditional validation
        try:
            validation = validate(
                query=query,
                answer=answer_text,
                chunks=chunks,
                provider=provider,
                model=model,
            )
            if not validation.get("grounded", True):
                disclaimer = "\n\n⚠️ *Note: This answer may not be fully supported by the uploaded documents.*"
                yield f"data: {disclaimer}\n\n"
                answer_text += disclaimer
        except Exception as e:
            logger.warning("Validation failed during stream: %s", e)

    # Send sources block
    if sources:
        yield "data: [SOURCES_START]\n\n"
        yield f"data: {json.dumps({'chunks': sources})}\n\n"

    # Save to memory
    memory.save_turn(session_id, query, answer_text)

    # Done
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint with SSE streaming.

    Streams raw text tokens, then sends sources as JSON, then [DONE].
    """
    return StreamingResponse(
        _generate_stream(
            query=request.query,
            session_id=request.session_id,
            provider=request.provider,
            model=request.model,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/sync")
async def chat_sync(request: ChatRequest):
    """
    Non-streaming chat endpoint (fallback).
    Runs the full agent synchronously and returns complete response.
    """
    result = run_agent(
        query=request.query,
        session_id=request.session_id,
        provider=request.provider,
        model=request.model,
    )
    return ChatResponse(
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        route=result.get("route", ""),
        session_id=request.session_id,
    )
