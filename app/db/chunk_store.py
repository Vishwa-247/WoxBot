"""
Chunk Store — MongoDB CRUD for document chunks and document records.

Collections:
  - woxbot.chunks  — individual text chunks with embeddings metadata
  - woxbot.documents — document-level records (filename, hash, status)

Provides:
  - save_chunks() — bulk insert chunks after ingestion
  - get_chunks_for_docs() — fetch chunks by doc_id list (for multi-doc filtering)
  - delete_chunks_by_doc() — remove all chunks for a document
  - save_document() — upsert a document record
  - list_documents() — list all indexed documents
  - get_document() — get a single document record
  - delete_document_record() — remove a document record
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db.mongo import get_db

logger = logging.getLogger("woxbot")


# ── Chunk Operations ─────────────────────────────────────────────────


async def save_chunks(chunks: list[dict]) -> int:
    """
    Bulk insert chunks into MongoDB.

    Each chunk dict should have: doc_id, chunk_id, filename, page,
    section_title, text, token_count, embedding_model_version.

    Returns number of chunks inserted.
    """
    db = get_db()
    if db is None:
        logger.warning("[ChunkStore] MongoDB not connected — skipping save_chunks.")
        return 0

    if not chunks:
        return 0

    now = datetime.now(timezone.utc)
    for c in chunks:
        c.setdefault("created_at", now)

    result = await db.chunks.insert_many(chunks)
    count = len(result.inserted_ids)
    logger.info("[ChunkStore] Inserted %d chunks.", count)
    return count


async def get_chunks_for_docs(doc_ids: list[str]) -> list[dict]:
    """
    Fetch all chunks for selected documents.

    Used by multi-document filtering in retrieval.
    """
    db = get_db()
    if db is None:
        return []

    cursor = db.chunks.find(
        {"doc_id": {"$in": doc_ids}},
        {"_id": 0},
    )
    return await cursor.to_list(length=None)


async def get_chunk_indices_for_docs(doc_ids: list[str]) -> list[int]:
    """
    Return the FAISS index positions for chunks belonging to selected docs.

    Requires that each chunk has a 'faiss_index' field stored at ingestion time.
    """
    db = get_db()
    if db is None:
        return []

    cursor = db.chunks.find(
        {"doc_id": {"$in": doc_ids}},
        {"faiss_index": 1, "_id": 0},
    )
    docs = await cursor.to_list(length=None)
    return [d["faiss_index"] for d in docs if "faiss_index" in d]


async def delete_chunks_by_doc(doc_id: str) -> int:
    """Delete all chunks for a document. Returns number removed."""
    db = get_db()
    if db is None:
        return 0

    result = await db.chunks.delete_many({"doc_id": doc_id})
    logger.info("[ChunkStore] Deleted %d chunks for doc_id=%s.", result.deleted_count, doc_id)
    return result.deleted_count


async def count_chunks_by_doc(doc_id: str) -> int:
    """Count chunks for a specific document."""
    db = get_db()
    if db is None:
        return 0
    return await db.chunks.count_documents({"doc_id": doc_id})


# ── Document Operations ──────────────────────────────────────────────


async def save_document(doc: dict) -> None:
    """
    Upsert a document record.

    doc should have: _id (sha256 hash), filename, total_pages,
    scanned_pages, chunk_count, status.
    """
    db = get_db()
    if db is None:
        return

    doc.setdefault("uploaded_at", datetime.now(timezone.utc))
    doc.setdefault("status", "indexed")

    await db.documents.update_one(
        {"_id": doc["_id"]},
        {"$set": doc},
        upsert=True,
    )
    logger.info("[ChunkStore] Saved document record: %s", doc.get("filename"))


async def list_documents() -> list[dict]:
    """List all indexed documents with metadata."""
    db = get_db()
    if db is None:
        return []

    cursor = db.documents.find({}, {"_id": 1, "filename": 1, "total_pages": 1,
                                     "chunk_count": 1, "uploaded_at": 1,
                                     "status": 1, "summary": 1})
    return await cursor.to_list(length=None)


async def get_document(doc_id: str) -> dict | None:
    """Get a single document record by ID."""
    db = get_db()
    if db is None:
        return None
    return await db.documents.find_one({"_id": doc_id})


async def delete_document_record(doc_id: str) -> bool:
    """Delete a document record. Returns True if found and deleted."""
    db = get_db()
    if db is None:
        return False

    result = await db.documents.delete_one({"_id": doc_id})
    return result.deleted_count > 0


async def ensure_indexes() -> None:
    """Create MongoDB indexes for performance."""
    db = get_db()
    if db is None:
        return

    await db.chunks.create_index([("doc_id", 1), ("chunk_id", 1)])
    await db.chunks.create_index("doc_id")
    await db.chunks.create_index("filename")
    await db.documents.create_index("filename")
    logger.info("[ChunkStore] MongoDB indexes ensured.")
