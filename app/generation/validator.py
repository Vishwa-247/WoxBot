"""
Validator — Conditional answer validation.

Pipeline (per build plan Fix 4):
  Step 1: Cheap deterministic check
    - Compute token overlap between answer and retrieved chunks
    - Compute cosine similarity between answer embedding and chunk embeddings
  Step 2: Only if similarity is borderline → call LLM validator
  Step 3: For high-confidence retrievals → skip validator entirely

NEVER call LLM validator on every answer — doubles cost and latency.
"""

from __future__ import annotations

import logging
import re

import numpy as np
from app.core.config import get_settings
from app.generation.llm import generate
from app.generation.prompt import VALIDATOR_PROMPT
from app.ingestion.embedder import embed_query

logger = logging.getLogger("woxbot")

# Thresholds for the deterministic check
HIGH_CONFIDENCE_THRESHOLD = 0.65
BORDERLINE_LOW = 0.40
TOKEN_OVERLAP_MIN = 0.15


def _tokenize(text: str) -> set[str]:
    """Simple lowercase word tokenization."""
    return set(re.findall(r"\b\w+\b", text.lower()))


def _token_overlap(answer: str, chunks: list[dict]) -> float:
    """
    Compute token overlap ratio between the answer and chunk texts.

    Returns fraction of answer tokens found in any chunk.
    """
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0

    chunk_tokens: set[str] = set()
    for chunk in chunks:
        chunk_tokens |= _tokenize(chunk.get("text", ""))

    overlap = answer_tokens & chunk_tokens
    # Exclude common stop words from ratio calculation
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "can", "shall",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "it", "this", "that", "and", "or", "but", "not", "if", "so"}
    meaningful_answer = answer_tokens - stop_words
    meaningful_overlap = overlap - stop_words

    if not meaningful_answer:
        return 1.0  # All tokens are stop words → consider grounded

    return len(meaningful_overlap) / len(meaningful_answer)


def _embedding_similarity(answer: str, chunks: list[dict]) -> float:
    """
    Compute average cosine similarity between the answer embedding
    and the embeddings of the top chunks.

    Uses the query embedder for a lightweight single-vector check.
    """
    answer_emb = embed_query(answer)  # shape (1, dim)

    # Re-embed chunk texts (lightweight — max 8 chunks)
    chunk_texts = [c.get("text", "") for c in chunks if c.get("text")]
    if not chunk_texts:
        return 0.0

    from app.ingestion.embedder import embed_texts
    chunk_embs = embed_texts(chunk_texts)  # shape (n, dim)

    # Normalize
    answer_norm = answer_emb / (np.linalg.norm(answer_emb, axis=1, keepdims=True) + 1e-10)
    chunk_norms = chunk_embs / (np.linalg.norm(chunk_embs, axis=1, keepdims=True) + 1e-10)

    # Cosine similarities
    similarities = (answer_norm @ chunk_norms.T).flatten()
    return float(np.mean(similarities))


def _llm_validate(query: str, answer: str, context: str, **kwargs) -> bool:
    """
    Call LLM validator — only for borderline cases.

    Returns True if grounded, False if ungrounded.
    """
    prompt = VALIDATOR_PROMPT.format(
        context=context,
        query=query,
        answer=answer,
    )
    result = generate(prompt, temperature=0.0, **kwargs)
    verdict = result.strip().lower()
    logger.info("LLM validator verdict: %s", verdict)
    return "grounded" in verdict


def validate(
    query: str,
    answer: str,
    chunks: list[dict],
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """
    Conditional validation of a generated answer.

    Returns:
        dict with keys:
          - grounded: bool
          - confidence: str ("high", "borderline", "low")
          - method: str ("token_overlap", "embedding", "llm", "skipped")
          - token_overlap: float
    """
    # Step 1: Token overlap (cheapest check)
    overlap = _token_overlap(answer, chunks)
    logger.info("Validator token overlap: %.3f", overlap)

    if overlap < TOKEN_OVERLAP_MIN:
        # Very low overlap — likely hallucinated
        return {
            "grounded": False,
            "confidence": "low",
            "method": "token_overlap",
            "token_overlap": overlap,
        }

    if overlap > 0.60:
        # High token overlap — very likely grounded, skip further checks
        return {
            "grounded": True,
            "confidence": "high",
            "method": "token_overlap",
            "token_overlap": overlap,
        }

    # Step 2: Embedding similarity (medium cost)
    try:
        sim = _embedding_similarity(answer, chunks)
        logger.info("Validator embedding similarity: %.3f", sim)
    except Exception as e:
        logger.warning("Embedding similarity check failed: %s", e)
        sim = 0.5  # Neutral fallback

    if sim >= HIGH_CONFIDENCE_THRESHOLD:
        return {
            "grounded": True,
            "confidence": "high",
            "method": "embedding",
            "token_overlap": overlap,
        }

    if sim < BORDERLINE_LOW:
        return {
            "grounded": False,
            "confidence": "low",
            "method": "embedding",
            "token_overlap": overlap,
        }

    # Step 3: Borderline — call LLM validator
    logger.info("Borderline confidence (sim=%.3f) — calling LLM validator.", sim)
    context = "\n\n".join(c.get("text", "") for c in chunks)
    kwargs: dict = {}
    if provider:
        kwargs["provider"] = provider
    if model:
        kwargs["model"] = model

    is_grounded = _llm_validate(query, answer, context, **kwargs)
    return {
        "grounded": is_grounded,
        "confidence": "borderline",
        "method": "llm",
        "token_overlap": overlap,
    }
