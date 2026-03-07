"""
PDF Loader — PyMuPDF text extraction with scanned page detection.

Extracts text page-by-page from PDF files.
Flags pages with < 50 characters as potential scans.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger("woxbot")

SCANNED_PAGE_THRESHOLD = 50  # chars — pages below this are flagged


@dataclass
class PageContent:
    """Represents extracted text from a single PDF page."""

    page_num: int
    text: str
    is_scanned: bool = False


@dataclass
class PDFDocument:
    """Represents a fully parsed PDF document."""

    filename: str
    pages: list[PageContent] = field(default_factory=list)
    scanned_pages: list[int] = field(default_factory=list)
    total_pages: int = 0


def load_pdf(file_path: str | Path) -> PDFDocument:
    """
    Extract text from a PDF using PyMuPDF.

    Args:
        file_path: Path to the PDF file.

    Returns:
        PDFDocument with page-level text and scanned page flags.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        RuntimeError: If PyMuPDF fails to open the file.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF: {path}") from exc

    pdf_doc = PDFDocument(filename=path.name, total_pages=len(doc))

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # plain text extraction

        is_scanned = len(text.strip()) < SCANNED_PAGE_THRESHOLD

        if is_scanned:
            pdf_doc.scanned_pages.append(page_num + 1)  # 1-indexed
            logger.warning(
                "Page %d of '%s' appears to be a scan — text may not be searchable.",
                page_num + 1,
                path.name,
            )

        pdf_doc.pages.append(
            PageContent(
                page_num=page_num + 1,  # 1-indexed for display
                text=text,
                is_scanned=is_scanned,
            )
        )

    doc.close()

    logger.info(
        "Loaded '%s': %d pages (%d scanned).",
        path.name,
        pdf_doc.total_pages,
        len(pdf_doc.scanned_pages),
    )

    return pdf_doc
