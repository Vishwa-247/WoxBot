"""
Ingest Route — POST /api/ingest for PDF upload and ingestion.

Accepts multipart PDF upload, runs the full ingestion pipeline:
  Load PDF → Chunk → Embed → FAISS + BM25
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.api.schemas import IngestResponse
from app.core.config import get_settings
from app.ingestion.chunking import chunk_document
from app.ingestion.embedder import embed_chunks
from app.ingestion.loader import load_pdf
from app.retrieval.bm25_store import build_and_save as build_bm25
from app.retrieval.vector_store import build_and_save, is_already_indexed

logger = logging.getLogger("woxbot")

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    """
    Upload and ingest a PDF into the knowledge base.

    Pipeline: Load → Chunk → Embed → FAISS + BM25
    Returns chunk count and scanned page warnings.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return IngestResponse(
            filename=file.filename or "unknown",
            chunks_added=0,
            total_pages=0,
            message="Only PDF files are supported.",
        )

    settings = get_settings()

    # Save uploaded file to data/raw/
    raw_dir = Path(settings.data_raw_path)
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest_path = raw_dir / file.filename

    content = await file.read()
    dest_path.write_bytes(content)
    logger.info("Saved uploaded file: %s (%d bytes)", dest_path, len(content))

    # Check dedup
    if is_already_indexed(dest_path):
        return IngestResponse(
            filename=file.filename,
            chunks_added=0,
            total_pages=0,
            message="Document already indexed (SHA-256 match). No changes made.",
        )

    # Load PDF
    pdf_doc = load_pdf(dest_path)

    # Chunk
    chunks = chunk_document(
        pdf_doc,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    if not chunks:
        return IngestResponse(
            filename=file.filename,
            chunks_added=0,
            total_pages=pdf_doc.total_pages,
            scanned_pages=pdf_doc.scanned_pages,
            message="No text chunks produced. File may be entirely scanned/image-based.",
        )

    # Embed
    embeddings = embed_chunks(chunks)

    # Save to FAISS
    added = build_and_save(chunks, embeddings, dest_path)

    # Rebuild BM25
    try:
        build_bm25()
        logger.info("BM25 index rebuilt after ingestion.")
    except Exception as e:
        logger.warning("BM25 rebuild failed: %s", e)

    logger.info(
        "Ingested '%s': %d chunks, %d pages, %d scanned.",
        file.filename,
        added,
        pdf_doc.total_pages,
        len(pdf_doc.scanned_pages),
    )

    return IngestResponse(
        filename=file.filename,
        chunks_added=added,
        total_pages=pdf_doc.total_pages,
        scanned_pages=pdf_doc.scanned_pages,
        message=f"Successfully indexed {added} chunks from {pdf_doc.total_pages} pages.",
    )
