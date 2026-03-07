# WoxBot — Complete Build Plan
**Agentic RAG Academic Assistant for Woxsen University**
Dara Eakeswar Rayudu · B.Tech CSE Data Science · March 2026
Stack: React + FastAPI + LangGraph + Gemini + FAISS + MCP

---

## ⚠️ READ THIS FIRST — 5 Critical Constraints

Before writing any code, lock in these 5 rules. Every architectural decision follows from them.

1. **Chunk size = 400 tokens, section-based** — detect headings first, chunk per section. NEVER use RecursiveTextSplitter blindly on all PDFs with a single token count.
2. **Reranker returns top 8 chunks, NOT top 3** — complex questions need context from multiple pages. Set `RERANK_TOP_K=8` in .env.
3. **Query Rewriter node is the FIRST step in LangGraph** — before the router, before retrieval. Converts vague follow-ups like "what is it" into standalone queries using conversation history.
4. **Never use `eval()` for the calculator** — use pure `list[float]` arithmetic only.
5. **All SSE streaming logic lives in `useStream.js` only** — never open EventSource inside a React component directly.

---

## Project Overview

WoxBot is a production-grade Agentic RAG system for Woxsen University students. Students upload course PDFs (syllabus, lab manuals, notes) and ask natural language questions. The system retrieves grounded answers with source citations — zero hallucination.

### Problem Statement
- Scattered information — 8 semesters of PDFs with no intelligent search
- ChatGPT hallucinations — generic LLMs answer from training data, not your Woxsen syllabus
- No 24/7 academic support

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 19 + Vite + TailwindCSS | UI, streaming, dark mode |
| Backend | FastAPI + Python 3.11 | API server, SSE streaming |
| LLM | Gemini 1.5 Flash | Answer generation |
| Embeddings | Gemini text-embedding-004 | Vector creation |
| Vector DB | FAISS (faiss-cpu) | Semantic search |
| Keyword Search | rank_bm25 | Exact match search |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Re-score top 20 → top 8 |
| Agent Framework | LangGraph 0.3+ | Agentic routing (ReAct) |
| PDF Parsing | PyMuPDF (fitz) | Text extraction |
| MCP Server | fastmcp | Expose RAG to Claude Desktop |
| Evaluation | RAGAS | Hallucination metrics |
| Deploy | Vercel (frontend) + Render (backend) | Hosting |

---

## Final Architecture

### Ingestion Pipeline
```
PDF Upload
  → Scanned Page Detection (flag pages with < 50 chars)
  → Layout-Aware Parsing (PyMuPDF)
  → Detect Headings (ALL CAPS / Title Case / Numbered like "1.", "1.1")
  → Section-Based Chunking (300–400 tokens per section)
  → Embed with Gemini text-embedding-004
  → Save to FAISS + BM25 + metadata.json
     (chunk_id → filename, page, section_title, text, embedding_model_version)
```

### Query / Chat Pipeline
```
Student Question
  → Query Rewriter        (standalone query from conversation history)
  → Keyword Pre-Router    (rule-based: my notes / CGPA / web?)
  → LangGraph Router      (document_qa / web_search / calculation / summarize / unclear)
  → Hybrid Retrieval      (FAISS top-20 + BM25 top-20 → RRF Fusion)
  → CrossEncoder Reranker (top 20 → top 8)
  → Similarity Threshold  (if all scores < calibrated_threshold → no_context fallback)
  → Anti-Hallucination Prompt + Gemini 1.5 Flash
  → Self-Correction Validator (ONLY on borderline confidence, not every answer)
  → Post-Hoc Source Mapping   (attach sources by sentence — NOT inline LLM citation)
  → SSE Token Stream → React Frontend
```

---

## Complete Folder Structure

```
woxbot/
├── frontend/
│   ├── public/
│   │   └── woxbot-logo.png
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx       # Reads state only — never touches EventSource
│   │   │   ├── MessageBubble.jsx    # User + bot bubbles with react-markdown
│   │   │   ├── InputBar.jsx         # Text input + send + mic icon
│   │   │   ├── FileUpload.jsx       # Drag-and-drop PDF uploader + progress
│   │   │   ├── SourcePanel.jsx      # Chunks + page + section title
│   │   │   ├── Sidebar.jsx          # Chat history (in-memory)
│   │   │   ├── DocumentList.jsx     # Indexed PDFs with delete button
│   │   │   ├── LoadingDots.jsx      # Typing indicator animation
│   │   │   └── Navbar.jsx           # Logo + dark/light toggle
│   │   ├── hooks/
│   │   │   ├── useChat.js           # Chat state, send message, session_id
│   │   │   ├── useStream.js         # ALL EventSource logic here — useRef guard
│   │   │   └── useUpload.js         # PDF upload state + progress
│   │   ├── services/
│   │   │   └── api.js               # All Axios calls to FastAPI
│   │   ├── utils/
│   │   │   └── markdown.js          # react-markdown config
│   │   ├── styles/
│   │   │   └── globals.css          # TailwindCSS base
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── .env                         # VITE_API_URL=http://localhost:8000
│   ├── index.html
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app: CORS, routers, startup
│   │   ├── config.py                # All env vars
│   │   ├── ingestion/
│   │   │   ├── loader.py            # PyMuPDF + scanned page detection
│   │   │   ├── chunking.py          # Section-based chunker (heading detection)
│   │   │   └── embedder.py          # Gemini text-embedding-004 → numpy vectors
│   │   ├── retrieval/
│   │   │   ├── vector_store.py      # FAISS: build, save, load + SHA-256 dedup
│   │   │   ├── bm25_store.py        # rank_bm25: build, save as pkl, search
│   │   │   ├── retriever.py         # Hybrid: FAISS(20) + BM25(20) → RRF merge
│   │   │   └── reranker.py          # CrossEncoder → top 8 (NOT top 3)
│   │   ├── agent/
│   │   │   ├── graph.py             # LangGraph StateGraph definition
│   │   │   ├── nodes.py             # rewriter, router, rag, search, calc, validate, stream
│   │   │   ├── tools.py             # Tool definitions (RAG, web, calculator)
│   │   │   ├── router.py            # Keyword pre-router + LLM router
│   │   │   └── memory.py            # Last 5 turns conversation buffer
│   │   ├── generation/
│   │   │   ├── llm.py               # Gemini 1.5 Flash: streaming + non-streaming
│   │   │   ├── prompt.py            # All prompts: anti-hallucination, rewriter, validator
│   │   │   └── validator.py         # Deterministic checks first → LLM only on borderline
│   │   ├── api/
│   │   │   ├── schemas.py           # Pydantic: ChatRequest, IngestResponse, SourceChunk
│   │   │   └── routes/
│   │   │       ├── chat.py          # POST /api/chat → SSE StreamingResponse
│   │   │       ├── ingest.py        # POST /api/ingest → PDF indexing
│   │   │       └── sources.py       # GET/DELETE /api/sources (auth required)
│   │   ├── evaluation/
│   │   │   ├── metrics.py           # RAGAS: faithfulness, recall, relevancy
│   │   │   ├── test_questions.json  # 200 Woxsen-specific Q&A pairs
│   │   │   └── evaluator.py         # Run RAGAS once, cache JSON output
│   │   └── utils/
│   │       ├── logger.py            # Structured logging: file + console
│   │       └── helpers.py           # Shared utilities
│   ├── data/
│   │   ├── raw/                     # Place Woxsen PDFs here
│   │   └── processed/               # Chunked JSON cache
│   ├── vector_db/
│   │   ├── faiss.index
│   │   ├── bm25.pkl
│   │   └── metadata.json            # chunk_id → filename, page, section, text, model_version
│   ├── tests/
│   │   ├── test_ingestion.py
│   │   ├── test_retrieval.py
│   │   └── test_rag_chain.py
│   ├── run_ingestion.py             # One-time: ingest all PDFs in data/raw/
│   ├── requirements.txt
│   └── .env
│
├── mcp_server/
│   ├── mcp_server.py                # FastMCP server
│   ├── tools/
│   │   ├── search_docs.py           # search_woxsen_docs tool
│   │   ├── ingest_pdf.py            # ingest_pdf tool
│   │   ├── list_documents.py        # list_documents tool
│   │   └── calculate.py             # calculate_cgpa — pure arithmetic, no eval()
│   └── README_MCP.md
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Environment Variables

```bash
# backend/.env
GEMINI_API_KEY=your_key_here
CHUNK_SIZE=400
CHUNK_OVERLAP=80
SIMILARITY_THRESHOLD=calibrate_from_data   # DO NOT hardcode 0.75
RERANK_TOP_K=8                             # NOT 3
RETRIEVAL_TOP_K=20
MAX_MEMORY_TURNS=5
VECTOR_DB_PATH=./vector_db
DATA_RAW_PATH=./data/raw
EMBEDDING_MODEL_VERSION=text-embedding-004
LOG_LEVEL=INFO

# frontend/.env
VITE_API_URL=http://localhost:8000
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | /api/health | None | `{status: "ok", version: "1.0"}` |
| POST | /api/ingest | Required | Upload PDF → index → return chunk count |
| POST | /api/chat | Required | SSE stream — tokens then sources |
| GET | /api/sources | Required | List indexed docs (paginated) |
| DELETE | /api/sources/{doc_id} | Required | Remove doc + wipe FAISS vectors |

### SSE Stream Format
```
data: The
data: round
data: -robin
data: [SOURCES_START]
data: {"chunks": [{"text": "...", "source": "OS_notes.pdf", "page": 12, "section": "Round Robin Scheduling"}]}
data: [DONE]
```
**Rule:** Send raw text tokens first. Then one JSON block for sources after `[SOURCES_START]` delimiter. Never send each token as JSON — this crashes React parsers.

---

## MCP Tools

| Tool | Input | Output |
|---|---|---|
| search_woxsen_docs | query: str | answer + source citations |
| ingest_pdf | file_path: str | chunks_indexed: int |
| list_documents | — | list of filenames |
| calculate_cgpa | marks: list[float] | cgpa: float |

---

## Anti-Hallucination System Prompt (Use This Exactly)

```
You are WoxBot, an academic assistant for Woxsen University students.

STRICT RULES:
1. Answer ONLY using the context provided below.
2. NEVER use outside knowledge for factual answers.
3. If the answer is not in the context, respond exactly:
   "I couldn't find this in your uploaded documents. Please upload the relevant notes."
4. Do NOT include [Source: filename, Page X] inline — sources are attached automatically after your response.
5. Do NOT make up page numbers, filenames, or any fact not in the context.

CONTEXT:
{retrieved_chunks}

CONVERSATION HISTORY:
{memory}

STUDENT QUESTION:
{query}
```

---

## Phase 1 — Project Setup
**Day 1 | Risk: LOW**

### Goal
Get the project skeleton running: folders, environment, CORS tested, health endpoint live, Gemini API verified.

### Files to Create
| File | What It Does |
|---|---|
| backend/app/main.py | FastAPI app with CORS, router includes, startup event |
| backend/app/config.py | Load all env vars using python-dotenv |
| backend/.env | All secrets and config values |
| backend/app/utils/logger.py | Structured logging to file + console |
| frontend/ | Init with Vite + TailwindCSS |

### Tasks
- [ ] Create Python virtual environment and install requirements.txt
- [ ] Set GEMINI_API_KEY in .env and test with a direct Gemini API call
- [ ] Create `/api/health` returning `{status: "ok", version: "1.0"}`
- [ ] **Test CORS from browser:** open devtools → `fetch('http://localhost:8000/api/health')` → must return 200 with no CORS error
- [ ] Init React app with Vite and TailwindCSS (blank page is fine)

### ❌ Do NOT
- Skip the CORS browser test — this causes 4 hours of debugging on Day 6

### ✅ Done When
Browser fetch to /api/health returns 200 with no CORS error. Gemini API responds. React blank page loads on localhost:5173.

---

## Phase 2 — Robust Ingestion Pipeline
**Day 2 | Risk: HIGH**

### Goal
Build PDF-to-FAISS pipeline with scanned page detection, section-aware chunking, and SHA-256 deduplication.

### Files to Create
| File | What It Does |
|---|---|
| backend/app/ingestion/loader.py | PyMuPDF + scanned page detection |
| backend/app/ingestion/chunking.py | Section-based chunker — heading detection first |
| backend/app/ingestion/embedder.py | Gemini text-embedding-004 → numpy float32 |
| backend/app/retrieval/vector_store.py | FAISS IndexFlatIP + SHA-256 dedup |
| backend/run_ingestion.py | One-time script: ingest all PDFs in data/raw/ |

### Critical Implementation Details

**Fix 1 — Section-Based Chunking**
```python
# Detect headings using regex BEFORE applying token limit
# Heading patterns: ALL CAPS, Title Case, lines starting with "1.", "1.1", "Chapter"
# Split at section boundaries first
# Then apply 300-400 token limit WITHIN each section
# Every chunk must start with its section title as context
# Libraries: unstructured, layoutparser, or simple regex
```

**Fix 2 — Scanned Page Detection**
```python
# After PyMuPDF extracts each page:
if len(text.strip()) < 50:
    flag_as_scanned(page_num)
    warn_user(f"Page {page_num} appears to be a scan — text may not be searchable.")
# Add pytesseract OCR as optional fallback
```

**Fix 3 — SHA-256 Deduplication**
```python
import hashlib
file_hash = hashlib.sha256(file_bytes).hexdigest()
# Check metadata.json for existing hash
# If found → skip re-indexing, return "Already indexed"
# Store hash in metadata.json per document
```

**Fix 4 — Store Embedding Model Version**
```python
# In metadata.json per chunk:
{
  "chunk_id": "...",
  "filename": "OS_notes.pdf",
  "page": 12,
  "section_title": "Round Robin Scheduling",
  "text": "...",
  "embedding_model_version": "text-embedding-004"  # ALWAYS store this
}
```

### Tasks
- [ ] Gather 10-15 real Woxsen PDFs (mix of digital + scanned)
- [ ] Test PyMuPDF on each — log which pages are scanned
- [ ] Implement section-based chunking — print sample chunks to verify structure
- [ ] Run full ingestion and verify metadata.json is populated with section titles
- [ ] Verify embedding_model_version is stored per chunk

### ❌ Do NOT
- Use RecursiveTextSplitter with a single 500-token size on all PDFs
- Skip SHA-256 hash check — duplicate chunks silently destroy retrieval quality

### ✅ Done When
FAISS index built. metadata.json has 100+ chunks with section titles. Sample chunks are coherent — not mid-sentence cuts. Scanned pages flagged correctly.

---

## Phase 3 — Hybrid Retrieval + Reranker
**Day 3 | Risk: HIGH**

### Goal
Build FAISS + BM25 + RRF fusion + CrossEncoder reranker. Test with real questions. Calibrate similarity threshold.

### Files to Create
| File | What It Does |
|---|---|
| backend/app/retrieval/bm25_store.py | rank_bm25 index: build, save as pkl, load, search |
| backend/app/retrieval/retriever.py | Hybrid: FAISS(20) + BM25(20) → RRF fusion |
| backend/app/retrieval/reranker.py | CrossEncoder → top 8 (NOT top 3) |
| experiments.ipynb | Test 10 real Woxsen questions, inspect chunks, calibrate threshold |

### Critical Implementation Details

**Fix — Reranker Top-K = 8**
```python
# In reranker.py:
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", 8))  # NOT 3

# Pipeline:
# FAISS(20) + BM25(20) → RRF fusion → CrossEncoder → return top 8
# Reason: Complex questions need context from multiple pages
# Gemini Flash handles large context well — more context = better answers
```

**Fix — Calibrate Threshold (NOT hardcoded 0.75)**
```python
# In experiments.ipynb:
# 1. Run 20 test questions
# 2. For each: note the FAISS similarity score of the CORRECT chunk
# 3. Plot distribution of scores
# 4. Pick threshold that catches 95% of correct answers
# 5. This calibrated value → SIMILARITY_THRESHOLD in .env
# It will NOT be 0.75 for Gemini text-embedding-004
```

### Tasks
- [ ] Build BM25 index from all chunks in metadata.json
- [ ] Implement RRF fusion: combine FAISS rank + BM25 rank scores
- [ ] Load CrossEncoder, rerank top-20 → return top 8
- [ ] Open experiments.ipynb: test 10 real questions, inspect returned chunks
- [ ] Run threshold calibration, set SIMILARITY_THRESHOLD in .env
- [ ] Benchmark CrossEncoder latency — must be under 1 second for 20 candidates

### ❌ Do NOT
- Hardcode RERANK_TOP_K = 3
- Use 0.75 as threshold without calibration

### ✅ Done When
10 test questions retrieve correct, coherent chunks in top-8. Threshold calibrated from data. CrossEncoder latency < 1s.

---

## Phase 4 — LangGraph Agent + Query Rewriter + Prompts
**Day 4 | Risk: HIGH**

### Goal
Build the complete LangGraph agent. Most importantly: add the Query Rewriter as the first node (missing from most RAG implementations), keyword pre-router, and post-hoc source mapping.

### Files to Create
| File | What It Does |
|---|---|
| backend/app/agent/graph.py | LangGraph StateGraph — all nodes and edges |
| backend/app/agent/nodes.py | rewriter, router, rag, search, calc, summarizer, clarify, validator, stream |
| backend/app/agent/tools.py | Tool definitions with Pydantic input schemas |
| backend/app/agent/router.py | Keyword pre-router + LLM router for ambiguous cases |
| backend/app/agent/memory.py | Last 5 turns conversation buffer |
| backend/app/generation/llm.py | Gemini 1.5 Flash: streaming + non-streaming, adapter interface |
| backend/app/generation/prompt.py | All prompt templates |
| backend/app/generation/validator.py | Deterministic checks first, LLM validator only on borderline |

### Critical Implementation Details

**Fix 1 — Query Rewriter (FIRST NODE — was missing from original PRD)**
```python
# This is the FIRST node in the graph — before router, before retrieval
# Prompt:
REWRITER_PROMPT = """
Rewrite the question as a standalone query using the conversation history.
If the question is already standalone, return it unchanged.

Conversation History:
{history}

Question: {query}

Standalone question:
"""
# Example: "what is it" + history about Round Robin → "What is Round Robin Scheduling?"
# This fixes ALL vague follow-up questions
```

**Fix 2 — Keyword Pre-Router**
```python
# Rule-based routing BEFORE hitting the LLM router
# Handles 90% of cases deterministically — LLM router only for ambiguous

def keyword_pre_route(query: str) -> str | None:
    q = query.lower()
    doc_keywords = ["my notes", "uploaded", "syllabus", "lab manual", "my pdf", "my document"]
    calc_keywords = ["cgpa", "marks", "gpa", "average", "calculate", "percentage"]
    web_keywords  = ["latest", "current", "news", "today", "recent", "2024", "2025", "2026"]

    if any(k in q for k in doc_keywords): return "document_qa"
    if any(k in q for k in calc_keywords): return "calculation"
    if any(k in q for k in web_keywords):  return "web_search"
    return None  # → pass to LLM router
```

**Fix 3 — Post-Hoc Source Mapping**
```python
# After LLM generates the answer:
# 1. Split answer into sentences
# 2. For each sentence: compute cosine similarity with each of the top-8 chunks
# 3. Assign the highest-scoring chunk as source for that sentence
# 4. Return sources alongside the answer
# NEVER instruct the LLM to write [Source: file.pdf, Page X] — it will hallucinate page numbers
```

**Fix 4 — Conditional Validator**
```python
# DO NOT call LLM validator on every answer — doubles cost and latency
# Step 1: Cheap deterministic check
#   - Compute token overlap between answer and retrieved chunks
#   - Compute cosine similarity between answer sentences and chunks
# Step 2: Only if similarity is borderline (between threshold and threshold+0.10)
#   → call LLM validator
# Step 3: For high-confidence retrievals (> threshold + 0.10)
#   → skip validator entirely
```

### LangGraph Node Flow
```
START
  → [Query Rewriter Node]       converts vague query to standalone
  → [Keyword Pre-Router]        rule-based fast routing
  → [LangGraph Router Node]     LLM routing for ambiguous cases
      ├── document_qa  → [RAG Node] → Hybrid Retrieval → Reranker(8) → LLM → Source Map
      ├── web_search   → [Search Node] → DuckDuckGo → LLM
      ├── calculation  → [Calculator Node] → pure float arithmetic → return result
      ├── summarize    → [Summarizer Node] → Map-Reduce over chunks → LLM
      └── unclear      → [Clarify Node] → ask user to rephrase
  → [Validator Node]            borderline cases only
  → [Memory Node]               save turn to buffer
  → [Stream Node]               SSE tokens to React
END
```

### Tasks
- [ ] Implement Query Rewriter as first node — test with 5 follow-up scenarios
- [ ] Build keyword pre-router with explicit rules
- [ ] Implement all 5 routing paths in LangGraph
- [ ] Write anti-hallucination prompt WITHOUT inline [Source:] instructions
- [ ] Implement post-hoc source mapping (sentence boundary + cosine sim)
- [ ] Implement deterministic validator — LLM validator only on borderline
- [ ] Test full agent in Python notebook with 10 queries including follow-ups

### ❌ Do NOT
- Use `eval()` for CGPA calculator — pure float arithmetic only
- Call LLM validator on every answer
- Instruct LLM to write [Source: filename.pdf, Page X] inline
- Open the LLM router without a keyword pre-filter

### ✅ Done When
Full agent handles all 5 routing paths. Follow-up questions rewritten correctly. Anti-hallucination prompt active. Sources attached post-hoc. Tested in notebook.

---

## Phase 5 — FastAPI Routes + SSE Streaming
**Day 5 | Risk: MEDIUM**

### Goal
Wire LangGraph agent to FastAPI endpoints. Implement SSE streaming. Test all endpoints with curl/Postman before touching the frontend.

### Files to Create
| File | What It Does |
|---|---|
| backend/app/api/schemas.py | Pydantic: ChatRequest, IngestResponse, SourceChunk, ChatStreamEvent |
| backend/app/api/routes/chat.py | POST /api/chat → SSE StreamingResponse |
| backend/app/api/routes/ingest.py | POST /api/ingest → multipart PDF → ingestion pipeline |
| backend/app/api/routes/sources.py | GET/DELETE /api/sources with auth |

### SSE Implementation Pattern
```python
# In chat.py — send raw text tokens, then one JSON block for sources
async def generate_stream(query: str, session_id: str):
    async for token in agent.stream(query, session_id):
        yield f"data: {token}\n\n"
    
    sources = agent.get_last_sources(session_id)
    yield f"data: [SOURCES_START]\n\n"
    yield f"data: {json.dumps({'chunks': sources})}\n\n"
    yield f"data: [DONE]\n\n"

# FastAPI route:
@router.post("/api/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        generate_stream(request.query, request.session_id),
        media_type="text/event-stream"
    )
```

### Tasks
- [ ] Build /api/chat SSE endpoint — test with: `curl -N http://localhost:8000/api/chat`
- [ ] Build /api/ingest: accept PDF multipart, call pipeline, return chunk count
- [ ] Build /api/sources: paginated list + delete that wipes FAISS + BM25 + metadata
- [ ] Add API key auth on all endpoints (header: `X-API-Key`)

### ❌ Do NOT
- Send each token as a JSON object `{"type":"token","content":"The"}` — parse this in React is fragile
- Expose raw file paths in /api/sources response

### ✅ Done When
curl shows streaming tokens in terminal. /api/ingest ingests a PDF and returns chunk count. All endpoints return 401 without auth header.

---

## Phase 6 — React Frontend
**Day 6 | Risk: MEDIUM**

### Goal
Build complete React UI. All SSE logic in useStream.js only. ChatWindow reads state only — never touches EventSource.

### Key Implementation Rules

**SSE in useStream.js — useRef Guard**
```javascript
// hooks/useStream.js
export function useStream() {
  const esRef = useRef(null);
  const [tokens, setTokens] = useState('');
  const [sources, setSources] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = useCallback((query, sessionId) => {
    // GUARD: prevent duplicate connections in React Strict Mode
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    setTokens('');
    setSources([]);
    setIsStreaming(true);

    const es = new EventSource(`/api/chat?query=${encodeURIComponent(query)}&session_id=${sessionId}`);
    esRef.current = es;

    es.onmessage = (event) => {
      if (event.data === '[DONE]') {
        setIsStreaming(false);
        es.close();
        esRef.current = null;
        return;
      }
      if (event.data === '[SOURCES_START]') return;
      if (event.data.startsWith('{"chunks"')) {
        setSources(JSON.parse(event.data).chunks);
        return;
      }
      setTokens(prev => prev + event.data);
    };

    // Cleanup
    return () => {
      es.close();
      esRef.current = null;
    };
  }, []);

  return { tokens, sources, isStreaming, startStream };
}
```

### Component Rules
- `ChatWindow.jsx` — reads `{ messages, isStreaming, sources }` from hooks. NEVER calls EventSource.
- `useStream.js` — ALL EventSource logic lives here. useRef guard prevents duplicates.
- `FileUpload.jsx` — drag-and-drop, show progress bar, show scanned page warnings from backend.
- `SourcePanel.jsx` — shows chunk text + filename + page number + section title.
- `Navbar.jsx` — dark/light toggle using TailwindCSS `dark:` classes.

### Tasks
- [ ] Build useStream.js with EventSource + useRef guard + cleanup
- [ ] Build ChatWindow.jsx reading state from hooks only
- [ ] Build FileUpload.jsx with drag-and-drop and progress
- [ ] Build SourcePanel.jsx with chunk + page + section
- [ ] Implement dark mode toggle
- [ ] Test: upload PDF → ask question → see tokens stream + sources appear

### ❌ Do NOT
- Open EventSource inside ChatWindow or any component directly

### ✅ Done When
Full demo works: upload PDF, ask question, tokens stream word-by-word, source panel shows chunk + page + section. Dark mode works.

---

## Phase 7 — MCP Server + RAGAS Evaluation + Deploy
**Day 7 | Risk: MEDIUM**

### Goal
Ship MCP server, run RAGAS evaluation once, deploy to Vercel + Render, write README.

### MCP Server (mcp_server/mcp_server.py)
```python
from fastmcp import FastMCP
mcp = FastMCP("WoxBot")

@mcp.tool()
def search_woxsen_docs(query: str) -> str:
    """Search uploaded Woxsen University documents and return a grounded answer."""
    # Calls the same RAG pipeline as the web app
    return rag_pipeline.run(query)

@mcp.tool()
def calculate_cgpa(marks: list[float]) -> float:
    """Calculate CGPA from a list of marks."""
    # Pure arithmetic — NO eval()
    return sum(marks) / len(marks)

@mcp.tool()
def list_documents() -> list[str]:
    """List all indexed document filenames."""
    return metadata_store.list_filenames()

@mcp.tool()
def ingest_pdf(file_path: str) -> int:
    """Index a new PDF into the knowledge base. Returns number of chunks created."""
    return ingestion_pipeline.run(file_path)
```

### MCP Security (Required)
- Add API key auth on all MCP tool calls
- Per-client scoping: clients only access explicitly shared documents
- Log every MCP call: client_id, tool, query, timestamp
- Rate limit: 20 requests/minute per client

### RAGAS Evaluation
```python
# Run ONCE and cache the output — do not re-run (costs API credits)
# Target scores:
# Faithfulness    > 0.85   (% answer sentences supported by context)
# Context Recall  > 0.80   (% correct chunks retrieved)
# Answer Relevancy > 0.80  (how directly answer addresses question)
# Hallucination Rate < 5%  (1 - Faithfulness)
```

### Deployment
- **Frontend → Vercel:** push to GitHub → connect Vercel → set `VITE_API_URL` to Render URL
- **Backend → Render:** push to GitHub → connect Render → add `GEMINI_API_KEY` env var
- **RAM limit:** lazy-load CrossEncoder (only import on first rerank call). Keep FAISS index < 50 PDFs on free tier (512MB RAM).

### Tasks
- [ ] Build MCP server with 4 tools + API key auth
- [ ] Test MCP connection from Claude Desktop
- [ ] Run evaluator.py — cache JSON output — screenshot scores for report
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Render with lazy CrossEncoder loading
- [ ] Test live URL end-to-end: upload → question → stream → sources
- [ ] Write README with demo link + RAGAS scores

### ✅ Done When
MCP connects to Claude Desktop. RAGAS Faithfulness > 0.85. Live Vercel URL works. README has demo link + scores.

---

## Master Checklist — Before Submission

### Architecture Fixes (All Must Be Done)
- [ ] Section-based chunking with heading detection — NOT blind RecursiveTextSplitter
- [ ] Scanned page detection: flag pages with < 50 chars, warn user
- [ ] SHA-256 deduplication before indexing any PDF
- [ ] Reranker returns top 8 — NOT top 3
- [ ] Query Rewriter node as FIRST step in LangGraph graph
- [ ] Keyword pre-router before LLM router
- [ ] Post-hoc source mapping — NOT inline LLM [Source:] citation
- [ ] Validator only on borderline confidence — NOT every answer
- [ ] Similarity threshold calibrated from data — NOT hardcoded 0.75
- [ ] No eval() in calculator — pure float arithmetic
- [ ] Auth on all FastAPI endpoints including /api/sources
- [ ] MCP auth + per-client scoping + audit logs
- [ ] Embedding model version stored in metadata.json
- [ ] SSE logic in useStream.js only — useRef guard against duplicates
- [ ] CORS tested from browser on Day 1

### Emergency Playbook
| Scenario | Action |
|---|---|
| Gemini API outage | Show "degraded mode" banner. Return cached answers if available. Never fail silently. |
| Render backend crash | Check RAM. Lazy-load CrossEncoder. Reduce FAISS index size. Restart. |
| FAISS index broken after model upgrade | Check embedding_model_version in metadata.json. Run reindex script. |
| Student reports wrong exam answer | Disable generation for that doc set. Check logs. Expand test suite. |

### Metrics to Log
| Priority | Metric | Target |
|---|---|---|
| 1 | Faithfulness (RAGAS) | > 0.85 |
| 2 | Retrieval Precision@8 | > 0.80 |
| 3 | No-context Rate | < 20% |
| 4 | Latency p95 (first token) | < 6s |
| 5 | Cost per query | Track weekly |

---

## Run Commands

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Add GEMINI_API_KEY
python run_ingestion.py         # Build FAISS index from PDFs in data/raw/
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env            # Set VITE_API_URL=http://localhost:8000
npm run dev                     # Opens on http://localhost:5173

# MCP Server (optional)
cd mcp_server
python mcp_server.py

# RAGAS Evaluation (run once, cache output)
cd backend
python app/evaluation/evaluator.py
```

---

*WoxBot Build Plan v3.0 — All fixes from 3 rounds of analysis included.*
*Start with Phase 1. Test the "Done When" condition before moving to the next phase.*
*Do not skip Phase 3 threshold calibration — it determines your entire system's accuracy.*

---

## Multi-LLM Provider Support (Added)

WoxBot supports multiple LLM backends via a unified adapter. The user selects the provider from a dropdown in the React UI. The backend routes to the correct provider based on the selection.

### Supported Providers

| Provider | Model | Free? | How |
|---|---|---|---|
| Gemini | gemini-1.5-flash | Yes (Google AI Studio free tier) | Direct API |
| Grok | grok-3 | Free trial available | xAI API |
| OpenRouter | Any model (Gemini, Llama, Mistral, etc.) | Free keys available | OpenRouter API |
| PHI-3 Local | phi3 (your laptop) | Free — runs locally | Ollama HTTP endpoint |

### Backend — LLM Adapter Pattern

```python
# backend/app/generation/llm.py

from enum import Enum

class LLMProvider(str, Enum):
    GEMINI     = "gemini"
    GROK       = "grok"
    OPENROUTER = "openrouter"
    LOCAL_PHI3 = "local_phi3"

class LLMAdapter:
    def __init__(self, provider: LLMProvider, model: str = None):
        self.provider = provider
        self.model = model

    async def generate(self, prompt: str, stream: bool = False):
        if self.provider == LLMProvider.GEMINI:
            return await self._gemini(prompt, stream)
        elif self.provider == LLMProvider.GROK:
            return await self._grok(prompt, stream)
        elif self.provider == LLMProvider.OPENROUTER:
            return await self._openrouter(prompt, stream)
        elif self.provider == LLMProvider.LOCAL_PHI3:
            return await self._local_phi3(prompt, stream)

    async def _gemini(self, prompt, stream):
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        if stream:
            return model.generate_content(prompt, stream=True)
        return model.generate_content(prompt).text

    async def _grok(self, prompt, stream):
        # Grok uses OpenAI-compatible API
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.GROK_API_KEY,
            base_url="https://api.x.ai/v1"
        )
        response = await client.chat.completions.create(
            model=self.model or "grok-3",
            messages=[{"role": "user", "content": prompt}],
            stream=stream
        )
        return response

    async def _openrouter(self, prompt, stream):
        # OpenRouter also uses OpenAI-compatible API
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        response = await client.chat.completions.create(
            model=self.model or "google/gemini-flash-1.5",  # free on OpenRouter
            messages=[{"role": "user", "content": prompt}],
            stream=stream,
            extra_headers={"HTTP-Referer": "https://woxbot.vercel.app"}
        )
        return response

    async def _local_phi3(self, prompt, stream):
        # PHI-3 via Ollama running on your laptop
        # Ollama exposes OpenAI-compatible endpoint at localhost:11434
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key="ollama",   # Ollama doesn't need a real key
            base_url="http://localhost:11434/v1"
        )
        response = await client.chat.completions.create(
            model=self.model or "phi3",
            messages=[{"role": "user", "content": prompt}],
            stream=stream
        )
        return response
```

### Updated .env — Add These Keys

```bash
# LLM Providers
GEMINI_API_KEY=your_gemini_key          # Google AI Studio — free
GROK_API_KEY=your_grok_key             # xAI free trial
OPENROUTER_API_KEY=your_openrouter_key  # openrouter.ai — free keys available
LOCAL_PHI3_URL=http://localhost:11434   # Ollama on your laptop

# Default provider (can be overridden per request from frontend dropdown)
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_LLM_MODEL=gemini-1.5-flash
```

### Updated Chat API — Accept Provider from Frontend

```python
# backend/app/api/schemas.py
class ChatRequest(BaseModel):
    query: str
    session_id: str
    provider: str = "gemini"    # comes from frontend dropdown
    model: str = None           # optional model override

# backend/app/api/routes/chat.py
@router.post("/api/chat")
async def chat(request: ChatRequest):
    llm = LLMAdapter(
        provider=LLMProvider(request.provider),
        model=request.model
    )
    agent = build_agent(llm=llm)
    return StreamingResponse(
        agent.stream(request.query, request.session_id),
        media_type="text/event-stream"
    )
```

### Frontend — Provider Dropdown in Navbar

```jsx
// src/components/Navbar.jsx
const PROVIDERS = [
  { value: "gemini",      label: "Gemini Flash",    tag: "Free",       model: "gemini-1.5-flash" },
  { value: "grok",        label: "Grok 3",          tag: "Trial",      model: "grok-3" },
  { value: "openrouter",  label: "OpenRouter",      tag: "Free keys",  model: "google/gemini-flash-1.5" },
  { value: "local_phi3",  label: "PHI-3 (Local)",   tag: "Offline",    model: "phi3" },
];

export function Navbar({ provider, setProvider }) {
  return (
    <nav>
      <span>WoxBot</span>
      <select
        value={provider}
        onChange={(e) => setProvider(e.target.value)}
        className="bg-gray-800 text-white rounded px-3 py-1 text-sm"
      >
        {PROVIDERS.map(p => (
          <option key={p.value} value={p.value}>
            {p.label} ({p.tag})
          </option>
        ))}
      </select>
    </nav>
  );
}
```

### Local PHI-3 Setup (One-Time)

```bash
# Install Ollama on your laptop: https://ollama.com
# Then pull PHI-3:
ollama pull phi3

# Verify it runs:
ollama run phi3 "Hello"

# Ollama now serves at http://localhost:11434
# WoxBot local_phi3 provider connects directly to this
```

### How to Get Free Keys

| Provider | Steps |
|---|---|
| Gemini (direct) | Go to aistudio.google.com → Get API key → Free tier: 15 req/min |
| Grok | Go to console.x.ai → Free trial credits available |
| OpenRouter | Go to openrouter.ai → Create account → Free tier with rate limits → Use model `google/gemini-flash-1.5` (free) |
| PHI-3 Local | Install Ollama → `ollama pull phi3` → No key needed |

### Which Provider to Use When

| Situation | Best Provider |
|---|---|
| Demo / submission | Gemini (most reliable, free) |
| Offline / no internet | PHI-3 Local via Ollama |
| Gemini quota exhausted | OpenRouter with Gemini model (same model, different quota) |
| Want to test Grok | Grok free trial |
| Multiple free quotas at once | OpenRouter (routes across providers) |

> **Important:** Embeddings always use Gemini text-embedding-004 regardless of which LLM provider is selected. The provider dropdown only controls the generation model, not the retrieval/embedding layer.

