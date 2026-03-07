"""
run_ingestion.py — One-time script to ingest all PDFs in data/raw/.

Usage:
    python run_ingestion.py

Processes each PDF through the full pipeline:
  1. Load PDF → extract text (PyMuPDF)
  2. Detect scanned pages (< 50 chars)
  3. Section-based chunking (heading detection → 400-token chunks)
  4. Embed with Gemini text-embedding-004
  5. Save to FAISS index + metadata.json (with SHA-256 dedup)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.core.logger import setup_logger
from app.ingestion.chunking import chunk_document
from app.ingestion.embedder import embed_chunks
from app.ingestion.loader import load_pdf
from app.retrieval.bm25_store import build_and_save as build_bm25
from app.retrieval.vector_store import build_and_save, is_already_indexed

logger = setup_logger("woxbot")


def ingest_all() -> None:
    """Ingest every PDF in the data/raw/ directory."""
    settings = get_settings()
    raw_dir = Path(settings.data_raw_path)

    if not raw_dir.exists():
        logger.error("Data directory not found: %s", raw_dir)
        print(f"ERROR: Create {raw_dir} and place your PDFs there.")
        return

    pdf_files = sorted(raw_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning("No PDF files found in %s", raw_dir)
        print(f"No PDFs found in {raw_dir}. Add your Woxsen course PDFs and re-run.")
        return

    print(f"\n{'='*60}")
    print(f"  WoxBot Ingestion Pipeline")
    print(f"  Found {len(pdf_files)} PDF(s) in {raw_dir}")
    print(f"{'='*60}\n")

    total_chunks = 0
    total_skipped = 0
    total_scanned_pages = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")

        # ── SHA-256 dedup check ──────────────────────────
        if is_already_indexed(pdf_path):
            print(f"  → Already indexed (SHA-256 match). Skipping.")
            total_skipped += 1
            continue

        # ── Step 1: Load PDF ─────────────────────────────
        pdf_doc = load_pdf(pdf_path)
        print(f"  → Loaded: {pdf_doc.total_pages} pages")

        if pdf_doc.scanned_pages:
            print(f"  ⚠ Scanned pages detected: {pdf_doc.scanned_pages}")
            total_scanned_pages += len(pdf_doc.scanned_pages)

        # ── Step 2: Section-based chunking ───────────────
        chunks = chunk_document(
            pdf_doc,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        print(f"  → Chunked: {len(chunks)} chunks")

        if not chunks:
            print(f"  ⚠ No chunks produced. File may be entirely scanned.")
            continue

        # ── Step 3: Embed with Gemini ────────────────────
        print(f"  → Embedding {len(chunks)} chunks...")
        embeddings = embed_chunks(chunks)
        print(f"  → Embeddings: shape {embeddings.shape}")

        # ── Step 4: Save to FAISS + metadata ─────────────
        added = build_and_save(chunks, embeddings, pdf_path)
        total_chunks += added
        print(f"  ✓ Indexed: {added} chunks added to FAISS\n")

    # ── Build BM25 index ──────────────────────────────────
    if total_chunks > 0:
        print("  Building BM25 keyword index...")
        bm25_count = build_bm25()
        print(f"  ✓ BM25 index built: {bm25_count} documents\n")

    # ── Summary ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Ingestion Complete")
    print(f"  PDFs processed: {len(pdf_files) - total_skipped}")
    print(f"  PDFs skipped (duplicate): {total_skipped}")
    print(f"  Total chunks indexed: {total_chunks}")
    print(f"  Scanned pages flagged: {total_scanned_pages}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    ingest_all()
