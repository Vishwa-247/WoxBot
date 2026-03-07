"""
Embedder — Gemini text-embedding-004 vector generation.

ALWAYS uses Gemini text-embedding-004 regardless of which LLM provider
is selected for generation (per architecture constraint).
"""

from __future__ import annotations

import logging
import time

from google import genai
import numpy as np

from app.core.config import get_settings
from app.ingestion.chunking import Chunk

logger = logging.getLogger("woxbot")

# Gemini embedding model — NEVER change per architecture constraint
EMBEDDING_MODEL = "text-embedding-004"
# Max texts per batch (Gemini API limit)
BATCH_SIZE = 100
# Delay between batches to avoid rate-limiting
BATCH_DELAY_SEC = 0.5


def _get_client() -> genai.Client:
    """Create a Gemini client with the API key."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")
    return genai.Client(api_key=settings.gemini_api_key)


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Generate embeddings for a list of texts using Gemini text-embedding-004.

    Args:
        texts: List of text strings to embed.

    Returns:
        numpy array of shape (len(texts), embedding_dim) with float32 vectors.
    """
    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info(
            "Embedding batch %d/%d (%d texts)...",
            i // BATCH_SIZE + 1,
            (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE,
            len(batch),
        )

        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config={"task_type": "RETRIEVAL_DOCUMENT"},
        )

        for emb in result.embeddings:
            all_embeddings.append(emb.values)

        # Rate-limit protection between batches
        if i + BATCH_SIZE < len(texts):
            time.sleep(BATCH_DELAY_SEC)

    vectors = np.array(all_embeddings, dtype=np.float32)
    logger.info("Generated %d embeddings (dim=%d).", vectors.shape[0], vectors.shape[1])
    return vectors


def embed_query(query: str) -> np.ndarray:
    """
    Embed a single query string for retrieval.

    Uses task_type="RETRIEVAL_QUERY" for better search performance.

    Args:
        query: The search query text.

    Returns:
        numpy array of shape (1, embedding_dim) with float32.
    """
    client = _get_client()

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config={"task_type": "RETRIEVAL_QUERY"},
    )

    vector = np.array([result.embeddings[0].values], dtype=np.float32)
    return vector


def embed_chunks(chunks: list[Chunk]) -> np.ndarray:
    """
    Convenience: embed a list of Chunk objects.

    Args:
        chunks: List of Chunk objects from the chunker.

    Returns:
        numpy array of shape (len(chunks), embedding_dim).
    """
    texts = [chunk.text for chunk in chunks]
    return embed_texts(texts)
