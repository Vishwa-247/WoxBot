"""
Reranker — CrossEncoder re-scoring of retrieval candidates.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
Pipeline: Takes top-20 hybrid results → re-scores → returns top 8 (NOT 3).

RERANK_TOP_K=8 per build plan constraint #2.
"""

from __future__ import annotations

import logging
import time

from sentence_transformers import CrossEncoder

from app.core.config import get_settings

logger = logging.getLogger("woxbot")

# Model is loaded once and cached at module level
_cross_encoder: CrossEncoder | None = None

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_cross_encoder() -> CrossEncoder:
    """Load CrossEncoder model (cached after first call)."""
    global _cross_encoder
    if _cross_encoder is None:
        logger.info("Loading CrossEncoder model: %s", CROSS_ENCODER_MODEL)
        start = time.time()
        _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
        elapsed = time.time() - start
        logger.info("CrossEncoder loaded in %.2fs.", elapsed)
    return _cross_encoder


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int | None = None,
) -> list[dict]:
    """
    Re-rank candidate chunks using CrossEncoder.

    Args:
        query: The original search query.
        candidates: List of chunk dicts from hybrid retrieval.
        top_k: Number of top results to return (default from settings.rerank_top_k).

    Returns:
        Top-k chunks sorted by CrossEncoder score descending.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.rerank_top_k  # 8 per constraint

    if not candidates:
        return []

    model = _get_cross_encoder()

    # Build (query, chunk_text) pairs for scoring
    pairs = [(query, chunk.get("text", "")) for chunk in candidates]

    start = time.time()
    scores = model.predict(pairs)
    elapsed = time.time() - start

    logger.info(
        "CrossEncoder reranked %d candidates in %.3fs.",
        len(candidates),
        elapsed,
    )

    # Attach scores and sort
    scored_candidates = []
    for chunk, score in zip(candidates, scores):
        result = chunk.copy()
        result["rerank_score"] = float(score)
        scored_candidates.append(result)

    scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

    return scored_candidates[:top_k]
