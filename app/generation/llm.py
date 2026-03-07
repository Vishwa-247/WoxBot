"""
LLM Adapter — Unified interface for multiple LLM providers.

Supports:
  - Gemini (google-genai SDK)
  - Groq (OpenAI-compatible)
  - OpenRouter (OpenAI-compatible)
  - PHI-3 local (Ollama, OpenAI-compatible)

Both streaming and non-streaming generation.
Provider/model can be overridden per request (frontend dropdown).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI, OpenAI

from app.core.config import get_settings

logger = logging.getLogger("woxbot")


# ── Provider Configs ─────────────────────────────────────────────────

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Default models per provider
DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-1.5-flash",
    "groq": "llama-3.1-8b-instant",
    "openrouter": "google/gemini-2.0-flash-001",
    "local": "phi3",
}


def _get_openai_client(provider: str, sync: bool = True) -> OpenAI | AsyncOpenAI:
    """Create an OpenAI-compatible client for the specified provider."""
    settings = get_settings()

    if provider == "groq":
        api_key = settings.grok_api_key
        base_url = GROQ_BASE_URL
    elif provider == "openrouter":
        api_key = settings.openrouter_api_key
        base_url = OPENROUTER_BASE_URL
    elif provider == "local":
        api_key = "ollama"
        base_url = settings.local_phi3_url + "/v1"
    else:
        raise ValueError(f"No OpenAI-compatible config for provider: {provider}")

    if sync:
        return OpenAI(api_key=api_key, base_url=base_url)
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


# ── Gemini Provider ──────────────────────────────────────────────────


def _generate_gemini(prompt: str, model: str, **kwargs: Any) -> str:
    """Generate with Gemini via google-genai SDK (non-streaming)."""
    from google import genai

    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text or ""


async def _stream_gemini(prompt: str, model: str, **kwargs: Any) -> AsyncGenerator[str, None]:
    """Stream with Gemini via google-genai SDK."""
    from google import genai

    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content_stream(
        model=model,
        contents=prompt,
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text


# ── OpenAI-Compatible Provider (Groq, OpenRouter, Local) ────────────


def _generate_openai_compat(prompt: str, model: str, provider: str, **kwargs: Any) -> str:
    """Generate with an OpenAI-compatible endpoint (non-streaming)."""
    client = _get_openai_client(provider, sync=True)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=kwargs.get("temperature", 0.3),
        max_tokens=kwargs.get("max_tokens", 2048),
    )
    return response.choices[0].message.content or ""


async def _stream_openai_compat(
    prompt: str, model: str, provider: str, **kwargs: Any
) -> AsyncGenerator[str, None]:
    """Stream with an OpenAI-compatible endpoint."""
    client = _get_openai_client(provider, sync=False)
    stream = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=kwargs.get("temperature", 0.3),
        max_tokens=kwargs.get("max_tokens", 2048),
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


# ── Public API ───────────────────────────────────────────────────────


def generate(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> str:
    """
    Generate a response from the LLM (non-streaming).

    Args:
        prompt: The full prompt text.
        provider: LLM provider (gemini, groq, openrouter, local).
                  Defaults to DEFAULT_LLM_PROVIDER from .env.
        model: Model name. Defaults to provider's default model.
        **kwargs: Extra params (temperature, max_tokens).

    Returns:
        Generated text string.
    """
    settings = get_settings()
    provider = (provider or settings.default_llm_provider).lower()
    model = model or DEFAULT_MODELS.get(provider, settings.default_llm_model)

    logger.info("LLM generate: provider=%s, model=%s", provider, model)

    if provider == "gemini":
        return _generate_gemini(prompt, model, **kwargs)
    return _generate_openai_compat(prompt, model, provider, **kwargs)


async def stream(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> AsyncGenerator[str, None]:
    """
    Stream a response from the LLM token by token.

    Args:
        prompt: The full prompt text.
        provider: LLM provider (gemini, groq, openrouter, local).
        model: Model name.
        **kwargs: Extra params (temperature, max_tokens).

    Yields:
        Text tokens as they arrive.
    """
    settings = get_settings()
    provider = (provider or settings.default_llm_provider).lower()
    model = model or DEFAULT_MODELS.get(provider, settings.default_llm_model)

    logger.info("LLM stream: provider=%s, model=%s", provider, model)

    if provider == "gemini":
        async for token in _stream_gemini(prompt, model, **kwargs):
            yield token
    else:
        async for token in _stream_openai_compat(prompt, model, provider, **kwargs):
            yield token
