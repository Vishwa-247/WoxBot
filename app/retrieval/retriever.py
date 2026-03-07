"""
Hybrid Retriever — FAISS (semantic) + BM25 (keyword) with RRF fusion.

Pipeline:
  1. FAISS top-20 (semantic similarity)
  2. BM25 top-20 (keyword match)
  3. Reciprocal Rank Fusion (RRF) to merge rankings
  4. Return fused top-k candidates for reranking
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.ingestion.embedder import embed_query
from app.retrieval import bm25_store
from app.retrieval import vector_store

logger = logging.getLogger("woxbot")

# RRF constant (standard value from the original paper)
RRF_K = 60


def _reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    id_key: str = "chunk_id",
    k: int = RRF_K,
) -> list[dict]:
    """
    Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank_i)) for each list where the doc appears.

    Args:
        ranked_lists: List of ranked result lists (each is list[dict]).
        id_key: Key to identify unique chunks.
        k: RRF constant (default 60).

    Returns:
        Fused results sorted by RRF score descending.
    """
    rrf_scores: dict[str, float] = {}
    chunk_lookup: dict[str, dict] = {}

    for results in ranked_lists:
        for rank, chunk in enumerate(results):
            cid = chunk.get(id_key, "")
            if not cid:
                continue
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            # Keep the first occurrence (preserves metadata)
            if cid not in chunk_lookup:
                chunk_lookup[cid] = chunk

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    fused = []
    for cid in sorted_ids:
        chunk = chunk_lookup[cid].copy()
        chunk["rrf_score"] = rrf_scores[cid]
        fused.append(chunk)

    return fused


def hybrid_retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """
    Hybrid retrieval: FAISS(20) + BM25(20) → RRF fusion.

    Args:
        query: The search query string.
        top_k: Number of fused results to return (default from settings).

    Returns:
        List of chunk dicts with rrf_score, sorted by score descending.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.retrieval_top_k

    # ── FAISS semantic search (top-20) ───────────────────
    query_embedding = embed_query(query)
    faiss_results = vector_store.search(query_embedding, top_k=20)
    logger.info("FAISS returned %d results.", len(faiss_results))

    # ── BM25 keyword search (top-20) ────────────────────
    bm25_results = bm25_store.search(query, top_k=20)
    logger.info("BM25 returned %d results.", len(bm25_results))

    # ── RRF Fusion ──────────────────────────────────────
    fused = _reciprocal_rank_fusion([faiss_results, bm25_results])

    # Trim to requested top_k
    fused = fused[:top_k]

    logger.info(
        "Hybrid retrieval: FAISS(%d) + BM25(%d) → RRF fusion → %d results.",
        len(faiss_results),
        len(bm25_results),
        len(fused),
    )

    return fused
