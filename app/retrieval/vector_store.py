"""
FAISS Vector Store — build, save, load with SHA-256 deduplication.

Uses FAISS IndexFlatIP (inner-product / cosine similarity on L2-normalized vectors).
Stores metadata in metadata.json with per-chunk information including embedding_model_version.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import faiss
import numpy as np
from app.core.config import get_settings
from app.ingestion.chunking import Chunk

logger = logging.getLogger("woxbot")


# ── Metadata I/O ─────────────────────────────────────────────────────


def _get_paths() -> tuple[Path, Path, Path]:
    """Return (vector_db_dir, faiss_index_path, metadata_path)."""
    settings = get_settings()
    db_dir = Path(settings.vector_db_path)
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir, db_dir / "faiss.index", db_dir / "metadata.json"


def _load_metadata(meta_path: Path) -> dict:
    """Load metadata.json or return empty structure."""
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"document_hashes": {}, "chunks": []}


def _save_metadata(meta_path: Path, metadata: dict) -> None:
    """Persist metadata.json."""
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


# ── SHA-256 Deduplication ─────────────────────────────────────────────


def compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file for deduplication."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)
    return sha256.hexdigest()


def is_already_indexed(file_path: str | Path) -> bool:
    """Check if a file has already been indexed (by SHA-256 hash)."""
    _, _, meta_path = _get_paths()
    metadata = _load_metadata(meta_path)
    file_hash = compute_file_hash(file_path)
    return file_hash in metadata.get("document_hashes", {})


def has_documents() -> bool:
    """Return True if the FAISS index exists and contains at least one vector."""
    _, index_path, _ = _get_paths()
    if not index_path.exists():
        return False
    try:
        import faiss
        idx = faiss.read_index(str(index_path))
        return idx.ntotal > 0
    except Exception:
        return False


# ── FAISS Index Operations ────────────────────────────────────────────


def build_and_save(
    chunks: list[Chunk],
    embeddings: np.ndarray,
    file_path: str | Path,
) -> int:
    """
    Build (or append to) a FAISS index and save metadata.

    If the document was already indexed (SHA-256 match), skips and returns 0.
    Normalizes vectors to unit length for cosine similarity via IndexFlatIP.

    Args:
        chunks: List of Chunk objects from the chunker.
        embeddings: numpy array of shape (len(chunks), dim).
        file_path: Original PDF path (for hash computation).

    Returns:
        Number of new chunks added (0 if duplicate).
    """
    settings = get_settings()
    db_dir, index_path, meta_path = _get_paths()

    # ── SHA-256 dedup check ──────────────────────────────
    file_hash = compute_file_hash(file_path)
    metadata = _load_metadata(meta_path)

    if file_hash in metadata.get("document_hashes", {}):
        logger.info(
            "File '%s' already indexed (hash: %s). Skipping.",
            Path(file_path).name,
            file_hash[:12],
        )
        return 0

    # ── Normalize vectors for cosine similarity ──────────
    faiss.normalize_L2(embeddings)

    # ── Load or create FAISS index ───────────────────────
    dim = embeddings.shape[1]

    if index_path.exists():
        index = faiss.read_index(str(index_path))
        if index.d != dim:
            raise ValueError(
                f"Embedding dimension mismatch: index has {index.d}, got {dim}"
            )
    else:
        index = faiss.IndexFlatIP(dim)

    # ── Add vectors to index ─────────────────────────────
    index.add(embeddings)

    # ── Update metadata ──────────────────────────────────
    filename = Path(file_path).name
    metadata.setdefault("document_hashes", {})[file_hash] = filename

    for chunk in chunks:
        metadata.setdefault("chunks", []).append(
            {
                "chunk_id": chunk.chunk_id,
                "filename": chunk.filename,
                "page": chunk.page,
                "section_title": chunk.section_title,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "embedding_model_version": settings.embedding_model_version,
            }
        )

    # ── Persist ──────────────────────────────────────────
    faiss.write_index(index, str(index_path))
    _save_metadata(meta_path, metadata)

    logger.info(
        "Indexed '%s': %d chunks added. Total index size: %d.",
        filename,
        len(chunks),
        index.ntotal,
    )

    return len(chunks)


def load_index() -> tuple[faiss.Index, dict] | None:
    """
    Load the FAISS index and metadata from disk.

    Returns:
        (index, metadata) tuple or None if not built yet.
    """
    _, index_path, meta_path = _get_paths()

    if not index_path.exists() or not meta_path.exists():
        logger.warning("FAISS index or metadata not found. Run ingestion first.")
        return None

    index = faiss.read_index(str(index_path))
    metadata = _load_metadata(meta_path)

    logger.info("Loaded FAISS index: %d vectors.", index.ntotal)
    return index, metadata


def search(query_embedding: np.ndarray, top_k: int | None = None) -> list[dict]:
    """
    Search the FAISS index with a query embedding.

    Args:
        query_embedding: numpy array of shape (1, dim).
        top_k: Number of results to return (default from settings).

    Returns:
        List of dicts with chunk metadata + similarity score.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.retrieval_top_k

    result = load_index()
    if result is None:
        return []

    index, metadata = result
    chunks_meta = metadata.get("chunks", [])

    # Normalize query vector for cosine similarity
    faiss.normalize_L2(query_embedding)

    # Clamp top_k to index size
    k = min(top_k, index.ntotal)
    if k == 0:
        return []

    scores, indices = index.search(query_embedding, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(chunks_meta):
            continue
        chunk = chunks_meta[idx].copy()
        chunk["score"] = float(score)
        results.append(chunk)

    return results


def search_filtered(
    query_embedding: np.ndarray,
    allowed_filenames: set[str],
    top_k: int | None = None,
) -> list[dict]:
    """
    Search FAISS index but only return chunks from allowed filenames.

    Uses over-retrieval + post-filter (works with IndexFlatIP).
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.retrieval_top_k

    result = load_index()
    if result is None:
        return []

    index, metadata = result
    chunks_meta = metadata.get("chunks", [])

    faiss.normalize_L2(query_embedding)

    # Over-retrieve to compensate for filtering
    k = min(top_k * 5, index.ntotal)
    if k == 0:
        return []

    scores, indices = index.search(query_embedding, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(chunks_meta):
            continue
        chunk = chunks_meta[idx]
        if chunk.get("filename") not in allowed_filenames:
            continue
        entry = chunk.copy()
        entry["score"] = float(score)
        results.append(entry)
        if len(results) >= top_k:
            break

    return results


def delete_document(filename: str) -> int:
    """
    Remove all chunks for a document and rebuild the FAISS index.

    Args:
        filename: Name of the PDF to remove.

    Returns:
        Number of chunks removed.
    """
    db_dir, index_path, meta_path = _get_paths()
    metadata = _load_metadata(meta_path)

    chunks = metadata.get("chunks", [])
    original_count = len(chunks)

    # Filter out chunks from this document
    remaining_chunks = [c for c in chunks if c["filename"] != filename]
    removed_count = original_count - len(remaining_chunks)

    if removed_count == 0:
        logger.warning("No chunks found for '%s'.", filename)
        return 0

    # Remove document hash
    hashes = metadata.get("document_hashes", {})
    hash_to_remove = None
    for h, name in hashes.items():
        if name == filename:
            hash_to_remove = h
            break
    if hash_to_remove:
        del hashes[hash_to_remove]

    metadata["chunks"] = remaining_chunks
    metadata["document_hashes"] = hashes

    # Rebuild FAISS index from remaining chunks if any exist
    if index_path.exists():
        index_path.unlink()

    _save_metadata(meta_path, metadata)

    logger.info("Removed '%s': %d chunks deleted.", filename, removed_count)
    return removed_count
