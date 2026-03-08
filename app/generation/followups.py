"""
Follow-Up Generator — suggest 3 follow-up questions after each answer.

Returns a JSON array of 3 question strings. Fails silently if generation fails.
"""

from __future__ import annotations

import json
import logging

from app.generation import llm

logger = logging.getLogger("woxbot")

FOLLOWUP_PROMPT = """\
Based on this Q&A exchange, suggest 3 natural follow-up questions a student might ask.
Make them specific and answerable from the same documents.

Original question: {query}
Answer summary: {answer_summary}

Return ONLY a JSON array of 3 strings. No preamble. Example:
["What are the advantages of Round Robin?", "How does quantum size affect performance?", "Compare Round Robin with FCFS"]"""


def generate_followups(
    query: str,
    answer: str,
    provider: str | None = None,
    model: str | None = None,
) -> list[str]:
    """Generate 3 follow-up question suggestions."""
    answer_summary = answer[:500]
    prompt = FOLLOWUP_PROMPT.format(query=query, answer_summary=answer_summary)

    try:
        raw = llm.generate(prompt, provider=provider, model=model, temperature=0.5, max_tokens=300)
        raw = raw.strip()
        # Try to extract JSON array
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            return json.loads(raw[start : end + 1])
        return json.loads(raw)
    except Exception as e:
        logger.debug("Follow-up generation failed: %s", e)
        return []
