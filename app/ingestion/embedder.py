"""
Embedder — Multi-provider embedding generation.

Supports:
  - Gemini text-embedding-004 (primary, per architecture constraint)
  - OpenRouter (OpenAI-compatible: text-embedding-3-small / 3-large)

Provider is selected via EMBEDDING_PROVIDER in .env.
When Gemini key is available, switch back to gemini + text-embedding-004.
"""

from __future__ import annotations

import logging
import time

import numpy as np
from openai import OpenAI

from app.core.config import get_settings
from app.ingestion.chunking import Chunk

logger = logging.getLogger("woxbot")

# Max texts per batch
BATCH_SIZE = 100
# Delay between batches to avoid rate-limiting
BATCH_DELAY_SEC = 0.5


# ── Provider: Gemini ─────────────────────────────────────────────────


def _embed_texts_gemini(texts: list[str], model: str) -> np.ndarray:
    """Embed using Gemini text-embedding-004 via google-genai SDK."""
    from google import genai

    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    client = genai.Client(api_key=settings.gemini_api_key)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info(
            "[Gemini] Embedding batch %d/%d (%d texts)...",
            i // BATCH_SIZE + 1,
            (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE,
            len(batch),
        )
        result = client.models.embed_content(
            model=model,
            contents=batch,
            config={"task_type": "RETRIEVAL_DOCUMENT"},
        )
        for emb in result.embeddings:
            all_embeddings.append(emb.values)
        if i + BATCH_SIZE < len(texts):
            time.sleep(BATCH_DELAY_SEC)

    return np.array(all_embeddings, dtype=np.float32)


def _embed_query_gemini(query: str, model: str) -> np.ndarray:
    """Embed a single query using Gemini."""
    from google import genai

    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    result = client.models.embed_content(
        model=model,
        contents=query,
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return np.array([result.embeddings[0].values], dtype=np.float32)


# ── Provider: OpenRouter (OpenAI-compatible) ─────────────────────────

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _get_openrouter_client() -> OpenAI:
    """Create an OpenAI-compatible client pointing to OpenRouter."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=OPENROUTER_BASE_URL,
    )


def _embed_texts_openrouter(texts: list[str], model: str) -> np.ndarray:
    """Embed using OpenRouter's OpenAI-compatible embeddings endpoint."""
    client = _get_openrouter_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info(
            "[OpenRouter] Embedding batch %d/%d (%d texts) with %s...",
            i // BATCH_SIZE + 1,
            (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE,
            len(batch),
            model,
        )
        response = client.embeddings.create(model=model, input=batch)
        for item in response.data:
            all_embeddings.append(item.embedding)
        if i + BATCH_SIZE < len(texts):
            time.sleep(BATCH_DELAY_SEC)

    return np.array(all_embeddings, dtype=np.float32)


def _embed_query_openrouter(query: str, model: str) -> np.ndarray:
    """Embed a single query using OpenRouter."""
    client = _get_openrouter_client()
    response = client.embeddings.create(model=model, input=[query])
    return np.array([response.data[0].embedding], dtype=np.float32)


# ── Public API ───────────────────────────────────────────────────────

_PROVIDERS = {
    "gemini": (_embed_texts_gemini, _embed_query_gemini),
    "openrouter": (_embed_texts_openrouter, _embed_query_openrouter),
}


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Generate embeddings for a list of texts.

    Provider and model are determined by EMBEDDING_PROVIDER and
    EMBEDDING_MODEL_VERSION in .env.

    Args:
        texts: List of text strings to embed.

    Returns:
        numpy array of shape (len(texts), embedding_dim) with float32 vectors.
    """
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    model = settings.embedding_model_version

    embed_fn, _ = _PROVIDERS.get(provider, (None, None))
    if embed_fn is None:
        raise ValueError(f"Unknown embedding provider: {provider}. Use: {list(_PROVIDERS)}")

    logger.info("Embedding %d texts with provider=%s, model=%s", len(texts), provider, model)
    vectors = embed_fn(texts, model)
    logger.info("Generated %d embeddings (dim=%d).", vectors.shape[0], vectors.shape[1])
    return vectors


def embed_query(query: str) -> np.ndarray:
    """
    Embed a single query string for retrieval.

    Args:
        query: The search query text.

    Returns:
        numpy array of shape (1, embedding_dim) with float32.
    """
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    model = settings.embedding_model_version

    _, query_fn = _PROVIDERS.get(provider, (None, None))
    if query_fn is None:
        raise ValueError(f"Unknown embedding provider: {provider}. Use: {list(_PROVIDERS)}")

    return query_fn(query, model)


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
