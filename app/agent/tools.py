"""
Tool Definitions — Calculator + Web Search + Source Mapper.

Calculator: Pure float arithmetic — NO eval() (Constraint #4).
Web Search: DuckDuckGo search wrapper.
Source Mapper: Post-hoc source mapping (Fix 3 from build plan).
"""

from __future__ import annotations

import logging
import re

import numpy as np

logger = logging.getLogger("woxbot")


# ── Calculator (NO eval() — Constraint #4) ───────────────────────────


def safe_calculate(expression: str) -> str:
    """
    Evaluate a simple arithmetic expression using pure float parsing.

    Supports:
      - Basic: +, -, *, /
      - CGPA: average of comma-separated numbers
      - Percentage: X% of Y
      - Sum of numbers

    NEVER uses eval(). Pure float arithmetic only.
    """
    expr = expression.strip()
    logger.info("Calculator input: '%s'", expr)

    # Pattern: "average of X, Y, Z" or "CGPA of X, Y, Z"
    avg_match = re.match(
        r"(?:average|mean|cgpa|gpa)\s+(?:of\s+)?(.+)",
        expr,
        re.IGNORECASE,
    )
    if avg_match:
        numbers = _extract_numbers(avg_match.group(1))
        if numbers:
            result = sum(numbers) / len(numbers)
            return f"Average of {numbers} = {result:.4f}"
        return "Could not parse numbers for averaging."

    # Pattern: "X% of Y"
    pct_match = re.match(r"([\d.]+)\s*%\s*of\s*([\d.]+)", expr, re.IGNORECASE)
    if pct_match:
        pct = float(pct_match.group(1))
        total = float(pct_match.group(2))
        result = (pct / 100.0) * total
        return f"{pct}% of {total} = {result:.4f}"

    # Pattern: "sum of X, Y, Z"
    sum_match = re.match(r"sum\s+(?:of\s+)?(.+)", expr, re.IGNORECASE)
    if sum_match:
        numbers = _extract_numbers(sum_match.group(1))
        if numbers:
            result = sum(numbers)
            return f"Sum of {numbers} = {result:.4f}"
        return "Could not parse numbers for summing."

    # Pattern: "percentage of X out of Y" or "X out of Y percentage"
    out_of_match = re.match(
        r"(?:percentage\s+of\s+)?([\d.]+)\s+out\s+of\s+([\d.]+)",
        expr,
        re.IGNORECASE,
    )
    if out_of_match:
        part = float(out_of_match.group(1))
        total = float(out_of_match.group(2))
        if total == 0:
            return "Cannot divide by zero."
        result = (part / total) * 100.0
        return f"{part} out of {total} = {result:.2f}%"

    # Pattern: Simple arithmetic "X op Y"
    arith_match = re.match(r"([\d.]+)\s*([+\-*/])\s*([\d.]+)", expr)
    if arith_match:
        a = float(arith_match.group(1))
        op = arith_match.group(2)
        b = float(arith_match.group(3))
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        elif op == "/":
            if b == 0:
                return "Cannot divide by zero."
            result = a / b
        else:
            return f"Unknown operator: {op}"
        return f"{a} {op} {b} = {result:.4f}"

    # Fallback: try to extract numbers and compute average
    numbers = _extract_numbers(expr)
    if numbers:
        avg = sum(numbers) / len(numbers)
        return f"Found numbers {numbers}. Average = {avg:.4f}, Sum = {sum(numbers):.4f}"

    return "Could not parse the expression. Please provide a simple arithmetic expression, e.g., 'average of 8.5, 9.0, 7.5' or '25% of 500'."


def _extract_numbers(text: str) -> list[float]:
    """Extract all float numbers from a text string."""
    return [float(n) for n in re.findall(r"[\d]+\.?[\d]*", text)]


# ── Web Search (DuckDuckGo) ──────────────────────────────────────────


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo.

    Args:
        query: Search query string.
        max_results: Maximum number of results.

    Returns:
        List of dicts with title, href, body.
    """
    from duckduckgo_search import DDGS

    logger.info("Web search: '%s' (max %d results)", query, max_results)
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "href": r.get("href", ""),
                "body": r.get("body", ""),
            })

    logger.info("Web search returned %d results.", len(results))
    return results


def format_search_results(results: list[dict]) -> str:
    """Format web search results into a text block for the LLM."""
    if not results:
        return "No search results found."

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   URL: {r['href']}")
        lines.append(f"   {r['body']}")
        lines.append("")
    return "\n".join(lines)


# ── Post-Hoc Source Mapping (Fix 3 from build plan) ──────────────────


def map_sources(
    answer: str,
    chunks: list[dict],
    return_embeddings: bool = False,
) -> "list[dict] | tuple[list[dict], np.ndarray | None]":
    """
    Post-hoc source mapping — assign sources AFTER LLM generates the answer.

    Pipeline:
      1. Split answer into sentences
      2. For each sentence: compute cosine similarity with each chunk
      3. Assign the highest-scoring chunk as source for that sentence

    Args:
        answer: The generated answer text.
        chunks: The top-k reranked chunks used for generation.
        return_embeddings: When True, return (sources, chunk_embs) so callers
            can reuse chunk_embs in the validator without a second API call.

    Returns:
        List of unique source dicts, or (sources, chunk_embs) when return_embeddings=True.
    """
    if not chunks or not answer.strip():
        return ([], None) if return_embeddings else []

    from app.ingestion.embedder import embed_texts

    # Split answer into sentences
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    sentences = [s for s in sentences if len(s.split()) > 3]  # Skip trivial fragments

    if not sentences:
        # Return all chunks as sources if no sentences to map
        result = _unique_sources(chunks)
        return (result, None) if return_embeddings else result

    # Embed sentences and chunks
    chunk_embs = None
    try:
        sent_embs = embed_texts(sentences)
        chunk_texts = [c.get("text", "") for c in chunks]
        chunk_embs = embed_texts(chunk_texts)
    except Exception as e:
        logger.warning("Source mapping embedding failed: %s. Returning all chunks.", e)
        result = _unique_sources(chunks)
        return (result, None) if return_embeddings else result

    # Normalize for cosine similarity
    sent_norms = sent_embs / (np.linalg.norm(sent_embs, axis=1, keepdims=True) + 1e-10)
    chunk_norms = chunk_embs / (np.linalg.norm(chunk_embs, axis=1, keepdims=True) + 1e-10)

    # Similarity matrix: (num_sentences, num_chunks)
    sim_matrix = sent_norms @ chunk_norms.T

    # For each sentence, find the best-matching chunk
    used_chunk_indices: set[int] = set()
    for i in range(len(sentences)):
        best_idx = int(np.argmax(sim_matrix[i]))
        used_chunk_indices.add(best_idx)

    # Build source list from matched chunks
    matched_chunks = [chunks[i] for i in sorted(used_chunk_indices)]
    result = _unique_sources(matched_chunks)
    return (result, chunk_embs) if return_embeddings else result


def _unique_sources(chunks: list[dict]) -> list[dict]:
    """Deduplicate sources by filename + page."""
    seen: set[str] = set()
    sources: list[str] = []
    result: list[dict] = []

    for chunk in chunks:
        filename = chunk.get("filename", "unknown")
        page = chunk.get("page", 0)
        key = f"{filename}:{page}"

        if key not in seen:
            seen.add(key)
            result.append({
                "filename": filename,
                "page": page,
                "section_title": chunk.get("section_title", ""),
                "chunk_text": chunk.get("text", "")[:200],
                "relevance_score": chunk.get("rerank_score", chunk.get("rrf_score", 0.0)),
            })

    return result
