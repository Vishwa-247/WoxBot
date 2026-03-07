"""
Section-Based Chunker — heading-aware chunking for academic PDFs.

Strategy (per build plan constraint #1):
  1. Detect headings (ALL CAPS, Title Case, numbered lines like "1.", "1.1", "Chapter")
  2. Split text at section boundaries FIRST
  3. Then apply 300-400 token limit WITHIN each section
  4. Every chunk starts with its section title as context
  5. NEVER use RecursiveTextSplitter blindly
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from app.ingestion.loader import PDFDocument

logger = logging.getLogger("woxbot")

# ── Heading detection patterns ────────────────────────────────────────
# Order matters — more specific patterns first
HEADING_PATTERNS: list[re.Pattern[str]] = [
    # Numbered headings: "1.", "1.1", "1.1.1", "Chapter 1", "Unit 1"
    re.compile(r"^(?:Chapter|Unit|Module|Section|Part)\s+\d+", re.IGNORECASE),
    re.compile(r"^\d+(?:\.\d+)*\.?\s+\S"),
    # ALL CAPS lines (min 3 chars, not just numbers/symbols)
    re.compile(r"^[A-Z][A-Z\s\-:,&]{2,}$"),
    # Title Case lines (at least 3 words, each capitalized)
    re.compile(r"^(?:[A-Z][a-zA-Z]*\s+){2,}[A-Z][a-zA-Z]*\s*$"),
]


@dataclass
class Chunk:
    """A single text chunk with metadata."""

    chunk_id: str
    text: str
    filename: str
    page: int
    section_title: str
    token_count: int


@dataclass
class Section:
    """A detected section with its title and accumulated text."""

    title: str
    start_page: int
    lines: list[str] = field(default_factory=list)


def _is_heading(line: str) -> bool:
    """Check if a line matches any heading pattern."""
    stripped = line.strip()
    if not stripped or len(stripped) < 3:
        return False
    # Skip lines that are just numbers or very short
    if stripped.replace(".", "").replace(" ", "").isdigit():
        return False
    return any(pattern.match(stripped) for pattern in HEADING_PATTERNS)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 4 characters (standard approximation)."""
    return max(1, len(text) // 4)


def _split_section_into_chunks(
    section: Section,
    filename: str,
    chunk_size: int = 400,
    chunk_overlap: int = 80,
) -> list[Chunk]:
    """
    Split a section's text into chunks respecting the token limit.

    Each chunk is prefixed with the section title for context.
    Splits at sentence boundaries when possible.
    """
    full_text = "\n".join(section.lines).strip()
    if not full_text:
        return []

    title_prefix = f"[{section.title}]\n" if section.title else ""
    title_tokens = _estimate_tokens(title_prefix)
    available_tokens = chunk_size - title_tokens

    if available_tokens <= 0:
        available_tokens = chunk_size

    # Split into sentences for cleaner boundaries
    sentences = re.split(r"(?<=[.!?])\s+", full_text)
    # Filter empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[Chunk] = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = _estimate_tokens(sentence)

        # If single sentence exceeds limit, force-add it as its own chunk
        if sentence_tokens > available_tokens:
            # Flush current buffer first
            if current_sentences:
                chunk_text = title_prefix + " ".join(current_sentences)
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        text=chunk_text,
                        filename=filename,
                        page=section.start_page,
                        section_title=section.title,
                        token_count=_estimate_tokens(chunk_text),
                    )
                )
                current_sentences = []
                current_tokens = 0

            # Add oversized sentence as its own chunk
            chunk_text = title_prefix + sentence
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    filename=filename,
                    page=section.start_page,
                    section_title=section.title,
                    token_count=_estimate_tokens(chunk_text),
                )
            )
            continue

        # Would adding this sentence exceed the limit?
        if current_tokens + sentence_tokens > available_tokens:
            # Flush current buffer
            chunk_text = title_prefix + " ".join(current_sentences)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    filename=filename,
                    page=section.start_page,
                    section_title=section.title,
                    token_count=_estimate_tokens(chunk_text),
                )
            )

            # Overlap: keep last few sentences
            overlap_sentences: list[str] = []
            overlap_tokens = 0
            for s in reversed(current_sentences):
                s_tokens = _estimate_tokens(s)
                if overlap_tokens + s_tokens > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_tokens += s_tokens

            current_sentences = overlap_sentences
            current_tokens = overlap_tokens

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Flush remaining
    if current_sentences:
        chunk_text = title_prefix + " ".join(current_sentences)
        chunks.append(
            Chunk(
                chunk_id=str(uuid.uuid4()),
                text=chunk_text,
                filename=filename,
                page=section.start_page,
                section_title=section.title,
                token_count=_estimate_tokens(chunk_text),
            )
        )

    return chunks


def chunk_document(
    pdf_doc: PDFDocument,
    chunk_size: int = 400,
    chunk_overlap: int = 80,
) -> list[Chunk]:
    """
    Chunk a parsed PDF using section-aware splitting.

    1. Scan all pages for heading lines
    2. Group text under detected sections
    3. Split each section into 300-400 token chunks
    4. Prefix each chunk with its section title

    Args:
        pdf_doc: Parsed PDFDocument from loader.
        chunk_size: Max tokens per chunk (default 400).
        chunk_overlap: Overlap tokens between consecutive chunks (default 80).

    Returns:
        List of Chunk objects with metadata.
    """
    sections: list[Section] = []
    current_section = Section(title="Introduction", start_page=1)

    for page in pdf_doc.pages:
        # Skip scanned pages (they have no usable text)
        if page.is_scanned:
            continue

        lines = page.text.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if _is_heading(stripped):
                # Save current section if it has content
                if current_section.lines:
                    sections.append(current_section)
                # Start new section
                current_section = Section(
                    title=stripped,
                    start_page=page.page_num,
                )
            else:
                current_section.lines.append(stripped)

    # Don't forget the last section
    if current_section.lines:
        sections.append(current_section)

    # Convert sections to chunks
    all_chunks: list[Chunk] = []
    for section in sections:
        section_chunks = _split_section_into_chunks(
            section=section,
            filename=pdf_doc.filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(section_chunks)

    logger.info(
        "Chunked '%s': %d sections → %d chunks.",
        pdf_doc.filename,
        len(sections),
        len(all_chunks),
    )

    return all_chunks
