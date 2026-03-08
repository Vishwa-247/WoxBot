"""
API Schemas — Pydantic models for request/response validation.

Used by chat, ingest, and sources routes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Chat ─────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """POST /api/chat request body."""
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", max_length=100)
    provider: str | None = Field(default=None, description="LLM provider override")
    model: str | None = Field(default=None, description="LLM model override")
    selected_doc_ids: list[str] = Field(default_factory=list, description="Filter retrieval to these docs")


class SourceChunk(BaseModel):
    """A single source chunk returned alongside the answer."""
    filename: str = ""
    page: int = 0
    section_title: str = ""
    chunk_text: str = ""
    relevance_score: float = 0.0


class ChatResponse(BaseModel):
    """Non-streaming chat response (fallback)."""
    answer: str
    sources: list[SourceChunk] = []
    route: str = ""
    session_id: str = ""


# ── Ingest ───────────────────────────────────────────────────────────


class IngestResponse(BaseModel):
    """POST /api/ingest response."""
    filename: str
    chunks_added: int
    total_pages: int
    scanned_pages: list[int] = []
    message: str = ""
    summary: str = ""


# ── Sources ──────────────────────────────────────────────────────────


class DocumentInfo(BaseModel):
    """A single indexed document."""
    doc_id: str = ""
    filename: str
    chunk_count: int


class SourcesListResponse(BaseModel):
    """GET /api/sources response."""
    documents: list[DocumentInfo] = []
    total_chunks: int = 0


class DeleteResponse(BaseModel):
    """DELETE /api/sources response."""
    filename: str
    chunks_removed: int
    message: str = ""
