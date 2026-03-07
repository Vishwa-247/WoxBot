"""
BM25 Store — keyword-based search using rank_bm25.

Builds a BM25 index from chunk texts, saves/loads as pickle.
Used alongside FAISS for hybrid retrieval (RRF fusion).
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path

from app.core.config import get_settings
from rank_bm25 import BM25Okapi

logger = logging.getLogger("woxbot")


def _get_paths() -> tuple[Path, Path, Path]:
    """Return (vector_db_dir, bm25_path, metadata_path)."""
    settings = get_settings()
    db_dir = Path(settings.vector_db_path)
    return db_dir, db_dir / "bm25.pkl", db_dir / "metadata.json"


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer for BM25."""
    return text.lower().split()


def build_and_save() -> int:
    """
    Build a BM25 index from all chunks in metadata.json and save as pickle.

    Returns:
        Number of chunks indexed.
    """
    db_dir, bm25_path, meta_path = _get_paths()

    if not meta_path.exists():
        logger.warning("metadata.json not found. Run ingestion first.")
        return 0

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    chunks = metadata.get("chunks", [])
    if not chunks:
        logger.warning("No chunks in metadata.json.")
        return 0

    # Tokenize all chunk texts
    corpus = [_tokenize(chunk["text"]) for chunk in chunks]

    # Build BM25 index
    bm25 = BM25Okapi(corpus)

    # Save as pickle
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f)

    logger.info("BM25 index built: %d documents. Saved to %s", len(corpus), bm25_path)
    return len(corpus)


def load_index() -> BM25Okapi | None:
    """Load the BM25 index from pickle."""
    _, bm25_path, _ = _get_paths()

    if not bm25_path.exists():
        logger.warning("BM25 index not found at %s. Build it first.", bm25_path)
        return None

    with open(bm25_path, "rb") as f:
        bm25 = pickle.load(f)  # noqa: S301 — trusted local file

    logger.info("Loaded BM25 index: %d documents.", bm25.corpus_size)
    return bm25


def search(query: str, top_k: int | None = None) -> list[dict]:
    """
    Search the BM25 index with a text query.

    Args:
        query: The search query string.
        top_k: Number of results (default from settings.retrieval_top_k).

    Returns:
        List of dicts with chunk metadata + BM25 score, sorted by score desc.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.retrieval_top_k

    bm25 = load_index()
    if bm25 is None:
        return []

    _, _, meta_path = _get_paths()
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    chunks_meta = metadata.get("chunks", [])

    # Tokenize query and get scores
    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)

    # Get top-k indices sorted by score descending
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        if idx < len(chunks_meta) and scores[idx] > 0:
            chunk = chunks_meta[idx].copy()
            chunk["bm25_score"] = float(scores[idx])
            results.append(chunk)

    return results
