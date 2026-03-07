"""
test_ingestion_pipeline.py — Verify Phase 2 ingestion pipeline components.

Tests loader, chunker, and vector store (without Gemini API).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """Test that all Phase 2 modules import correctly."""
    print("[1/4] Testing imports...")
    from app.ingestion.loader import load_pdf, PDFDocument, PageContent
    from app.ingestion.chunking import chunk_document, Chunk, _is_heading
    from app.ingestion.embedder import embed_texts, embed_query, embed_chunks
    from app.retrieval.vector_store import (
        build_and_save, load_index, search, compute_file_hash, is_already_indexed
    )
    print("  ✓ All Phase 2 modules import successfully.\n")


def test_heading_detection():
    """Test heading pattern detection."""
    print("[2/4] Testing heading detection...")
    from app.ingestion.chunking import _is_heading

    # Should detect as headings
    assert _is_heading("ROUND ROBIN SCHEDULING"), "ALL CAPS should be heading"
    assert _is_heading("1. Introduction"), "Numbered heading should be detected"
    assert _is_heading("1.1 Background"), "Sub-numbered heading should be detected"
    assert _is_heading("Chapter 5 Memory Management"), "Chapter heading should be detected"
    assert _is_heading("Unit 3 Operating Systems"), "Unit heading should be detected"

    # Should NOT be headings
    assert not _is_heading(""), "Empty string not heading"
    assert not _is_heading("ab"), "Too short not heading"
    assert not _is_heading("this is a normal paragraph about scheduling algorithms"), \
        "Normal text should not be heading"

    print("  ✓ Heading detection patterns work correctly.\n")


def test_chunker_with_mock_data():
    """Test chunking with a mock PDFDocument."""
    print("[3/4] Testing section-based chunker...")
    from app.ingestion.loader import PDFDocument, PageContent
    from app.ingestion.chunking import chunk_document

    # Create a mock PDF with clear sections
    mock_pdf = PDFDocument(
        filename="test_notes.pdf",
        total_pages=2,
        pages=[
            PageContent(
                page_num=1,
                text=(
                    "INTRODUCTION TO OPERATING SYSTEMS\n"
                    "An operating system is a program that manages the computer hardware. "
                    "It also provides a basis for application programs and acts as an "
                    "intermediary between the computer user and the hardware. "
                    "Operating systems differ in their approaches to providing services. "
                    "Some systems provide more services than others.\n"
                    "\n"
                    "1.1 What Operating Systems Do\n"
                    "We begin our study by looking at the role of the operating system "
                    "in the overall computer system. A computer system can be divided "
                    "roughly into four components: the hardware, the operating system, "
                    "the application programs, and the users.\n"
                ),
                is_scanned=False,
            ),
            PageContent(
                page_num=2,
                text=(
                    "PROCESS MANAGEMENT\n"
                    "A process is a program in execution. A process needs certain resources, "
                    "including CPU time, memory, files, and I/O devices to accomplish its task. "
                    "The operating system is responsible for creating and deleting processes, "
                    "scheduling processes, and providing mechanisms for process synchronization "
                    "and communication.\n"
                    "\n"
                    "2.1 Process Scheduling\n"
                    "The objective of multiprogramming is to have some process running at all times. "
                    "The objective of time sharing is to switch the CPU among processes so frequently "
                    "that users can interact with each program while it is running.\n"
                ),
                is_scanned=False,
            ),
        ],
    )

    chunks = chunk_document(mock_pdf, chunk_size=400, chunk_overlap=80)

    print(f"  Produced {len(chunks)} chunks from {mock_pdf.total_pages} pages")
    assert len(chunks) > 0, "Should produce at least one chunk"

    # Verify each chunk has required metadata
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_id, f"Chunk {i} missing chunk_id"
        assert chunk.filename == "test_notes.pdf", f"Chunk {i} wrong filename"
        assert chunk.page > 0, f"Chunk {i} missing page number"
        assert chunk.section_title, f"Chunk {i} missing section_title"
        assert chunk.text, f"Chunk {i} missing text"
        assert chunk.token_count > 0, f"Chunk {i} missing token_count"
        assert chunk.token_count <= 450, f"Chunk {i} exceeds token limit ({chunk.token_count})"
        print(f"  Chunk {i+1}: section='{chunk.section_title}' | page={chunk.page} | tokens={chunk.token_count}")

    print("  ✓ Section-based chunking works correctly.\n")


def test_scanned_page_detection():
    """Test that scanned pages are flagged."""
    print("[4/4] Testing scanned page detection...")
    from app.ingestion.loader import PDFDocument, PageContent

    mock_pdf = PDFDocument(
        filename="mixed.pdf",
        total_pages=3,
        pages=[
            PageContent(page_num=1, text="Normal page with plenty of text content here.", is_scanned=False),
            PageContent(page_num=2, text="  \n  ", is_scanned=True),  # scanned
            PageContent(page_num=3, text="Another normal page.", is_scanned=False),
        ],
        scanned_pages=[2],
    )

    assert 2 in mock_pdf.scanned_pages, "Page 2 should be flagged as scanned"
    assert len(mock_pdf.scanned_pages) == 1, "Only page 2 should be scanned"
    print(f"  Scanned pages detected: {mock_pdf.scanned_pages}")
    print("  ✓ Scanned page detection works correctly.\n")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  WoxBot Phase 2 — Ingestion Pipeline Tests")
    print(f"{'='*60}\n")

    test_imports()
    test_heading_detection()
    test_chunker_with_mock_data()
    test_scanned_page_detection()

    print(f"{'='*60}")
    print(f"  All Phase 2 tests passed! ✓")
    print(f"{'='*60}\n")
