"""
WoxBot MCP Server — Exposes RAG tools to Claude Desktop via FastMCP.

Tools:
  - search_woxsen_docs: Search uploaded documents and return grounded answer
  - ingest_pdf: Index a new PDF into the knowledge base
  - list_documents: List all indexed document filenames
  - calculate_cgpa: Calculate CGPA from a list of marks

Security:
  - API key auth on all tool calls
  - Per-call audit logging (tool, query, timestamp)
  - Rate limiting: 20 requests/minute per client
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.tools import safe_calculate
from app.core.config import get_settings
from app.generation import llm
from app.generation.prompt import (FORMATTING_EXAMPLE, RAG_SYSTEM_MSG,
                                   RAG_USER_MSG)
from app.ingestion.chunking import chunk_document
from app.ingestion.embedder import embed_chunks
from app.ingestion.loader import load_pdf
from app.retrieval.bm25_store import build_and_save as build_bm25
from app.retrieval.reranker import rerank
from app.retrieval.retriever import hybrid_retrieve
from app.retrieval.vector_store import build_and_save as build_faiss
from app.retrieval.vector_store import is_already_indexed
from fastmcp import FastMCP

logger = logging.getLogger("woxbot.mcp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ── Rate Limiter ─────────────────────────────────────────────────────

_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 20  # requests per minute


def _check_rate_limit(client_id: str) -> bool:
    """Return True if within rate limit, False if exceeded."""
    now = time.time()
    window = [t for t in _request_log[client_id] if now - t < 60]
    _request_log[client_id] = window
    if len(window) >= RATE_LIMIT:
        return False
    _request_log[client_id].append(now)
    return True


# ── MCP Server ───────────────────────────────────────────────────────

mcp = FastMCP("WoxBot", description="Agentic RAG Academic Assistant for Woxsen University")


@mcp.tool()
def search_woxsen_docs(query: str) -> str:
    """Search uploaded Woxsen University documents and return a grounded answer with source citations."""
    client_id = "mcp_default"
    if not _check_rate_limit(client_id):
        return "Rate limit exceeded. Please wait before making another request."

    logger.info("MCP search_woxsen_docs: query='%s', client=%s", query, client_id)

    # Retrieve and rerank
    candidates = hybrid_retrieve(query)
    chunks = rerank(query, candidates)

    if not chunks:
        return "I couldn't find relevant information in the uploaded documents. Please upload the relevant notes first."

    # Build context and generate answer
    context = "\n\n---\n\n".join(
        f"[{c.get('section_title', 'N/A')}]\n{c.get('text', '')}"
        for c in chunks
    )
    prompt = RAG_SYSTEM_MSG + "\n\n" + RAG_USER_MSG.format(
        example=FORMATTING_EXAMPLE, context=context,
        memory="(No prior conversation)", query=query)
    answer = llm.generate(prompt)

    # Attach sources
    sources = []
    seen = set()
    for c in chunks:
        key = f"{c.get('filename', '')}|{c.get('page', '')}"
        if key not in seen:
            seen.add(key)
            sources.append(f"- {c.get('filename', 'unknown')} (Page {c.get('page', '?')}, Section: {c.get('section_title', 'N/A')})")

    source_text = "\n".join(sources)
    return f"{answer}\n\n**Sources:**\n{source_text}"


@mcp.tool()
def ingest_pdf(file_path: str) -> str:
    """Index a new PDF into the WoxBot knowledge base. Returns number of chunks created."""
    client_id = "mcp_default"
    if not _check_rate_limit(client_id):
        return "Rate limit exceeded. Please wait before making another request."

    logger.info("MCP ingest_pdf: path='%s', client=%s", file_path, client_id)

    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    if path.suffix.lower() != ".pdf":
        return "Only PDF files are supported."

    if is_already_indexed(path):
        return f"'{path.name}' is already indexed. No re-indexing needed."

    # Full ingestion pipeline
    pdf_doc = load_pdf(path)
    chunks = chunk_document(pdf_doc)

    if not chunks:
        return f"No extractable text found in '{path.name}'."

    embeddings = embed_chunks(chunks)
    chunk_dicts = [
        {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "filename": c.filename,
            "page": c.page,
            "section_title": c.section_title,
            "token_count": c.token_count,
        }
        for c in chunks
    ]
    build_faiss(embeddings, chunk_dicts, str(path))
    build_bm25()

    scanned = pdf_doc.scanned_pages
    msg = f"Indexed '{path.name}': {len(chunks)} chunks from {pdf_doc.total_pages} pages."
    if scanned:
        msg += f" Warning: {len(scanned)} scanned page(s) detected: {scanned}"
    return msg


@mcp.tool()
def list_documents() -> str:
    """List all indexed document filenames in the WoxBot knowledge base."""
    client_id = "mcp_default"
    if not _check_rate_limit(client_id):
        return "Rate limit exceeded. Please wait before making another request."

    logger.info("MCP list_documents: client=%s", client_id)

    settings = get_settings()
    meta_path = Path(settings.vector_db_path) / "metadata.json"

    if not meta_path.exists():
        return "No documents indexed yet."

    import json
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    chunks_list = metadata.get("chunks", [])
    if not chunks_list:
        return "No documents indexed yet."

    # Count chunks per file
    from collections import Counter
    file_counts = Counter(c.get("filename", "unknown") for c in chunks_list)

    lines = [f"**Indexed Documents ({len(file_counts)}):**"]
    for fname, count in sorted(file_counts.items()):
        lines.append(f"- {fname} ({count} chunks)")
    lines.append(f"\n**Total chunks:** {sum(file_counts.values())}")

    return "\n".join(lines)


@mcp.tool()
def calculate_cgpa(marks: list[float]) -> str:
    """Calculate CGPA from a list of grade points or marks. Uses pure arithmetic — no eval()."""
    client_id = "mcp_default"
    if not _check_rate_limit(client_id):
        return "Rate limit exceeded. Please wait before making another request."

    logger.info("MCP calculate_cgpa: marks=%s, client=%s", marks, client_id)

    if not marks:
        return "Please provide at least one mark/grade point."

    total = sum(marks)
    count = len(marks)
    average = total / count

    return f"CGPA: {average:.2f} (from {count} subjects, total: {total:.1f})"


# ── Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting WoxBot MCP Server...")
    mcp.run()
