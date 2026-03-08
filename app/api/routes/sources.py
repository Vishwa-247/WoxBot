"""
Sources Route — GET /api/sources + DELETE /api/sources/{filename}.

Lists indexed documents and allows deleting them.
Does NOT expose raw file paths (per build plan).
"""

from __future__ import annotations

import logging

from app.api.schemas import DeleteResponse, DocumentInfo, SourcesListResponse
from app.db import chunk_store
from app.retrieval.bm25_store import build_and_save as rebuild_bm25
from app.retrieval.vector_store import delete_document
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("woxbot")

router = APIRouter()


@router.get("/sources", response_model=SourcesListResponse)
async def list_sources():
    """
    List all indexed documents with chunk counts.

    Reads from MongoDB documents collection.
    Does NOT expose raw file paths — only filenames.
    """
    docs = await chunk_store.list_documents()

    documents = [
        DocumentInfo(
            doc_id=d.get("_id", ""),
            filename=d.get("filename", "unknown"),
            chunk_count=d.get("chunk_count", 0),
        )
        for d in docs
    ]

    total_chunks = sum(d.chunk_count for d in documents)

    return SourcesListResponse(
        documents=documents,
        total_chunks=total_chunks,
    )


@router.delete("/sources/{filename}", response_model=DeleteResponse)
async def delete_source(filename: str):
    """
    Delete an indexed document and its chunks from FAISS + BM25 + MongoDB.
    """
    removed = delete_document(filename)

    if removed == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{filename}' not found in the index.",
        )

    # Remove from MongoDB
    docs = await chunk_store.list_documents()
    for doc in docs:
        if doc.get("filename") == filename:
            doc_id = doc["_id"]
            await chunk_store.delete_chunks_by_doc(doc_id)
            await chunk_store.delete_document_record(doc_id)
            break

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
