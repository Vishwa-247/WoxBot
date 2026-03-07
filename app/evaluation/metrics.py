"""
RAG Evaluation Metrics — Faithfulness, Context Recall, Answer Relevancy.

Implements RAGAS-style metrics WITHOUT requiring the ragas library.
Uses embedding similarity + token overlap for cost-efficient evaluation.

Target scores (from build plan):
  - Faithfulness    > 0.85  (% answer sentences supported by context)
  - Context Recall  > 0.80  (% correct chunks retrieved)
  - Answer Relevancy > 0.80 (how directly answer addresses question)
  - Hallucination Rate < 5% (1 - Faithfulness)
"""

from __future__ import annotations

import logging
import re

import numpy as np

logger = logging.getLogger("woxbot.eval")

# Stop words excluded from overlap
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "it", "its", "this", "that",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "they", "them", "their", "what", "which", "who", "whom",
})


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    return [w for w in re.findall(r"\b\w+\b", text.lower()) if w not in _STOP_WORDS]


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


# ── Faithfulness ─────────────────────────────────────────────────────


def faithfulness(answer: str, context_chunks: list[str]) -> float:
    """
    Measure what fraction of answer sentences are supported by context.

    For each answer sentence, check token overlap with any context chunk.
    A sentence is "supported" if overlap ratio > 0.3.

    Returns:
        Float in [0, 1]. Higher = more grounded.
    """
    sentences = _split_sentences(answer)
    if not sentences:
        return 1.0  # Empty answer is trivially faithful

    context_text = " ".join(context_chunks)
    context_tokens = set(_tokenize(context_text))

    supported = 0
    for sent in sentences:
        sent_tokens = set(_tokenize(sent))
        if not sent_tokens:
            supported += 1
            continue
        overlap = len(sent_tokens & context_tokens) / len(sent_tokens)
        if overlap > 0.3:
            supported += 1

    return supported / len(sentences)


# ── Context Recall ───────────────────────────────────────────────────


def context_recall(answer: str, context_chunks: list[str]) -> float:
    """
    Measure how much of the context was actually used in the answer.

    For each context chunk, check if its key tokens appear in the answer.
    Higher = retrieval was more relevant.

    Returns:
        Float in [0, 1].
    """
    if not context_chunks:
        return 0.0

    answer_tokens = set(_tokenize(answer))
    if not answer_tokens:
        return 0.0

    used = 0
    for chunk in context_chunks:
        chunk_tokens = set(_tokenize(chunk))
        if not chunk_tokens:
            continue
        overlap = len(chunk_tokens & answer_tokens) / len(chunk_tokens)
        if overlap > 0.1:
            used += 1

    return used / len(context_chunks)


# ── Answer Relevancy ─────────────────────────────────────────────────


def answer_relevancy(question: str, answer: str) -> float:
    """
    Measure how directly the answer addresses the question.

    Uses token overlap between question and answer as a proxy.
    If the answer contains key question terms, it's likely relevant.

    Returns:
        Float in [0, 1].
    """
    q_tokens = set(_tokenize(question))
    a_tokens = set(_tokenize(answer))

    if not q_tokens:
        return 1.0

    # Fraction of question tokens present in answer
    overlap = len(q_tokens & a_tokens) / len(q_tokens)

    # Boost: long answers that address the question well
    length_bonus = min(len(a_tokens) / 50, 0.2)  # max 0.2 bonus

    return min(overlap + length_bonus, 1.0)


# ── Hallucination Rate ───────────────────────────────────────────────


def hallucination_rate(answer: str, context_chunks: list[str]) -> float:
    """
    Hallucination rate = 1 - Faithfulness.

    Returns:
        Float in [0, 1]. Lower = better.
    """
    return 1.0 - faithfulness(answer, context_chunks)


# ── Aggregate Scorer ─────────────────────────────────────────────────


def score_single(
    question: str,
    answer: str,
    context_chunks: list[str],
) -> dict:
    """
    Score a single QA pair across all metrics.

    Returns:
        Dict with faithfulness, context_recall, answer_relevancy, hallucination_rate.
    """
    f = faithfulness(answer, context_chunks)
    cr = context_recall(answer, context_chunks)
    ar = answer_relevancy(question, answer)
    hr = 1.0 - f

    return {
        "faithfulness": round(f, 4),
        "context_recall": round(cr, 4),
        "answer_relevancy": round(ar, 4),
        "hallucination_rate": round(hr, 4),
    }


def score_batch(results: list[dict]) -> dict:
    """
    Aggregate scores across a batch of QA results.

    Args:
        results: List of dicts, each with 'question', 'answer', 'context_chunks'.

    Returns:
        Dict with average scores + per-question breakdown.
    """
    scores = []
    for r in results:
        s = score_single(
            r["question"],
            r["answer"],
            r.get("context_chunks", []),
        )
        s["question"] = r["question"][:80]
        scores.append(s)

    if not scores:
        return {"error": "No results to score"}

    avg = {
        "avg_faithfulness": round(np.mean([s["faithfulness"] for s in scores]), 4),
        "avg_context_recall": round(np.mean([s["context_recall"] for s in scores]), 4),
        "avg_answer_relevancy": round(np.mean([s["answer_relevancy"] for s in scores]), 4),
        "avg_hallucination_rate": round(np.mean([s["hallucination_rate"] for s in scores]), 4),
        "total_questions": len(scores),
    }

    return {
        "summary": avg,
        "per_question": scores,
    }
