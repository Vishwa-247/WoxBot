"""
Auto-Summary — generate a document summary after PDF ingestion.

Called in ingest route after chunks are indexed. Stores summary in MongoDB.
"""

from __future__ import annotations

import logging

from app.db import chunk_store
from app.generation import llm

logger = logging.getLogger("woxbot")

AUTO_SUMMARY_PROMPT = """You are WoxBot. A student just uploaded a document.
Based on the content below, provide:

## What This Document Contains
- Subject and main topics covered
- Key chapters or units (list them)
- Type: notes / syllabus / lab manual / question paper

## 3 Questions You Can Ask Me About This Document
List 3 specific, useful questions this document can answer.

Keep the summary concise. Use bullet points.

Document content (first 10 chunks):
{sample_chunks}"""


async def generate_doc_summary(doc_id: str, chunks: list[dict]) -> str:
    """Generate a summary for a newly uploaded document and save to MongoDB."""
    sample_text = "\n\n".join(c.get("text", "") for c in chunks[:10])
    prompt = AUTO_SUMMARY_PROMPT.format(sample_chunks=sample_text)

    try:
        summary = llm.generate(prompt, temperature=0.3, max_tokens=600)
        if summary:
            await chunk_store.save_document({"_id": doc_id, "summary": summary})
            logger.info("Auto-summary generated for doc_id=%s", doc_id[:12])
            return summary
    except Exception as e:
        logger.warning("Auto-summary failed for doc_id=%s: %s", doc_id[:12], e)

    return ""
