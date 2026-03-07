"""
RAG Evaluation Runner — Run test questions through the pipeline and score results.

Usage:
    python -m app.evaluation.evaluator

Runs test_questions.json through the RAG pipeline, scores with RAGAS-style metrics,
and caches results to evaluation_results.json.

Run ONCE and cache output — do not re-run (costs API credits).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.tools import safe_calculate
from app.core.config import get_settings
from app.core.logger import setup_logger
from app.evaluation.metrics import score_batch
from app.generation import llm
from app.generation.prompt import RAG_SYSTEM_PROMPT, SUMMARIZER_PROMPT, WEB_SEARCH_PROMPT
from app.retrieval.reranker import rerank
from app.retrieval.retriever import hybrid_retrieve

logger = setup_logger("woxbot.eval")

EVAL_DIR = Path(__file__).parent
QUESTIONS_PATH = EVAL_DIR / "test_questions.json"
RESULTS_PATH = EVAL_DIR / "evaluation_results.json"


def _run_document_qa(question: str, provider: str | None = None, model: str | None = None) -> dict:
    """Run a document_qa question through the RAG pipeline."""
    candidates = hybrid_retrieve(question)
    chunks = rerank(question, candidates)

    context_chunks = [c.get("text", "") for c in chunks]

    if not chunks:
        return {
            "answer": "I don't have enough information in the uploaded documents to answer this.",
            "context_chunks": [],
            "route": "document_qa",
        }

    context = "\n\n---\n\n".join(
        f"[{c.get('section_title', 'N/A')}]\n{c.get('text', '')}"
        for c in chunks
    )
    prompt = RAG_SYSTEM_PROMPT.format(context=context, query=question)
    answer = llm.generate(prompt, provider=provider, model=model)

    return {
        "answer": answer,
        "context_chunks": context_chunks,
        "route": "document_qa",
    }


def _run_summarize(question: str, provider: str | None = None, model: str | None = None) -> dict:
    """Run a summarize question."""
    candidates = hybrid_retrieve(question, top_k=30)
    chunks = rerank(question, candidates, top_k=8)

    context_chunks = [c.get("text", "") for c in chunks]

    if not chunks:
        return {
            "answer": "I don't have enough document content to summarize.",
            "context_chunks": [],
            "route": "summarize",
        }

    content = "\n\n---\n\n".join(c.get("text", "") for c in chunks)
    prompt = SUMMARIZER_PROMPT.format(content=content)
    answer = llm.generate(prompt, provider=provider, model=model)

    return {
        "answer": answer,
        "context_chunks": context_chunks,
        "route": "summarize",
    }


def _run_calculation(question: str) -> dict:
    """Run a calculation question."""
    result = safe_calculate(question)
    return {
        "answer": result,
        "context_chunks": [],
        "route": "calculation",
    }


def _run_web_search(question: str) -> dict:
    """Run a web search question (skip scoring — no ground truth)."""
    return {
        "answer": "(web search — skipped for evaluation)",
        "context_chunks": [],
        "route": "web_search",
        "skipped": True,
    }


def run_evaluation(
    provider: str | None = None,
    model: str | None = None,
    limit: int | None = None,
) -> dict:
    """
    Run all test questions through the pipeline and score results.

    Args:
        provider: LLM provider override (groq, openrouter, etc.)
        model: Model name override.
        limit: Max number of questions to evaluate (for quick testing).

    Returns:
        Dict with summary scores + per-question breakdown.
    """
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if limit:
        questions = questions[:limit]

    logger.info("Starting evaluation: %d questions", len(questions))
    start_time = time.time()

    results = []
    skipped = 0

    for i, q in enumerate(questions):
        qtext = q["question"]
        category = q.get("category", "document_qa")

        logger.info("[%d/%d] %s → %s", i + 1, len(questions), category, qtext[:60])

        try:
            if category == "calculation":
                result = _run_calculation(qtext)
            elif category == "web_search":
                result = _run_web_search(qtext)
                skipped += 1
            elif category == "summarize":
                result = _run_summarize(qtext, provider=provider, model=model)
            else:
                result = _run_document_qa(qtext, provider=provider, model=model)

            result["question"] = qtext
            result["category"] = category
            result["id"] = q.get("id", i + 1)
            results.append(result)

        except Exception as e:
            logger.error("Error on question %d: %s", i + 1, e)
            results.append({
                "question": qtext,
                "answer": f"ERROR: {e}",
                "context_chunks": [],
                "route": category,
                "category": category,
                "id": q.get("id", i + 1),
                "error": str(e),
            })

    elapsed = time.time() - start_time

    # Score only non-skipped, non-error results with context
    scoreable = [r for r in results if not r.get("skipped") and not r.get("error")]
    scores = score_batch(scoreable)

    # Build final output
    output = {
        "metadata": {
            "total_questions": len(questions),
            "evaluated": len(scoreable),
            "skipped": skipped,
            "errors": len(results) - len(scoreable) - skipped,
            "elapsed_seconds": round(elapsed, 2),
            "provider": provider or "default",
            "model": model or "default",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "scores": scores.get("summary", {}),
        "targets": {
            "faithfulness": "> 0.85",
            "context_recall": "> 0.80",
            "answer_relevancy": "> 0.80",
            "hallucination_rate": "< 0.05",
        },
        "per_question": scores.get("per_question", []),
        "raw_results": results,
    }

    # Cache results
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info("Evaluation complete. Results saved to %s", RESULTS_PATH)

    # Print summary
    summary = output["scores"]
    print("\n" + "=" * 60)
    print("  WoxBot RAG Evaluation Results")
    print("=" * 60)
    print(f"  Questions evaluated: {output['metadata']['evaluated']}")
    print(f"  Time: {elapsed:.1f}s")
    print()
    if summary:
        print(f"  Faithfulness:      {summary.get('avg_faithfulness', 'N/A'):.4f}  (target > 0.85)")
        print(f"  Context Recall:    {summary.get('avg_context_recall', 'N/A'):.4f}  (target > 0.80)")
        print(f"  Answer Relevancy:  {summary.get('avg_answer_relevancy', 'N/A'):.4f}  (target > 0.80)")
        print(f"  Hallucination:     {summary.get('avg_hallucination_rate', 'N/A'):.4f}  (target < 0.05)")
    print("=" * 60)

    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run WoxBot RAG evaluation")
    parser.add_argument("--provider", default=None, help="LLM provider (groq, openrouter)")
    parser.add_argument("--model", default=None, help="Model name")
    parser.add_argument("--limit", type=int, default=None, help="Max questions to evaluate")
    args = parser.parse_args()

    run_evaluation(provider=args.provider, model=args.model, limit=args.limit)
