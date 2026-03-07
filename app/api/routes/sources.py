"""
Sources Route — GET /api/sources + DELETE /api/sources/{filename}.

Lists indexed documents and allows deleting them.
Does NOT expose raw file paths (per build plan ❌ Do NOT rule).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from app.api.schemas import DeleteResponse, DocumentInfo, SourcesListResponse
from app.core.config import get_settings
from app.retrieval.bm25_store import build_and_save as rebuild_bm25
from app.retrieval.vector_store import delete_document
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("woxbot")

router = APIRouter()


def _load_metadata() -> dict:
    """Load vector_db/metadata.json."""
    settings = get_settings()
    meta_path = Path(settings.vector_db_path) / "metadata.json"
    if not meta_path.exists():
        return {"chunks": [], "document_hashes": {}}
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/sources", response_model=SourcesListResponse)
async def list_sources():
    """
    List all indexed documents with chunk counts.

    Does NOT expose raw file paths — only filenames.
    """
    metadata = _load_metadata()
    chunks = metadata.get("chunks", [])

    # Count chunks per filename
    counts: Counter = Counter(c.get("filename", "unknown") for c in chunks)

    documents = [
        DocumentInfo(filename=name, chunk_count=count)
        for name, count in sorted(counts.items())
    ]

    return SourcesListResponse(
        documents=documents,
        total_chunks=len(chunks),
    )


@router.delete("/sources/{filename}", response_model=DeleteResponse)
async def delete_source(filename: str):
    """
    Delete an indexed document and its chunks from FAISS + BM25.

    Removes:
      1. Chunks from metadata.json
      2. Document hash entry
      3. Rebuilds BM25 index
    Note: FAISS index needs rebuild after delete (IndexFlatIP doesn't support removal).
    """
    removed = delete_document(filename)

    if removed == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{filename}' not found in the index.",
        )

    # Rebuild BM25 after deletion
    try:
        rebuild_bm25()
        logger.info("BM25 index rebuilt after deleting '%s'.", filename)
    except Exception as e:
        logger.warning("BM25 rebuild after delete failed: %s", e)

    logger.info("Deleted '%s': %d chunks removed.", filename, removed)

    return DeleteResponse(
        filename=filename,
        chunks_removed=removed,
        message=f"Removed {removed} chunks for '{filename}'.",
    )
