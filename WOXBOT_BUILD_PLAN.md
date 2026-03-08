# WoxBot — Phase 8 Upgrade Plan
**Agentic RAG Academic Assistant for Woxsen University**
Dara Eakeswar Rayudu · B.Tech CSE Data Science · March 2026
Stack: React + FastAPI + LangGraph + Gemini/Grok + FAISS + MongoDB + MCP

---

## ⚠️ READ THIS FIRST — Context for Opus 4.6

You are continuing work on WoxBot — a production-grade Agentic RAG system already built through 7 phases. All 7 phases are complete. This document adds **4 production upgrades** (Phase 8). Implement them in the order listed at the bottom.

**Existing constraints that STILL apply:**
1. Chunk size = 400 tokens, section-based. NEVER use RecursiveTextSplitter blindly.
2. Reranker returns top 8 chunks (`RERANK_TOP_K=8`). NOT top 3.
3. Query Rewriter is the FIRST node in LangGraph — before router, before retrieval.
4. Never use `eval()` for calculator — pure `list[float]` arithmetic only.
5. All SSE logic lives in `useStream.js` only — never open EventSource inside a React component.

---

## Overview — 4 Upgrades

| # | Upgrade | Problem It Solves | Priority |
|---|---|---|---|
| 1 | MongoDB Integration | `metadata.json` breaks at scale, no query support, can't delete specific doc chunks | HIGH |
| 2 | Multi-Document Selection | Bot searches ALL docs — slow, pulls irrelevant chunks from wrong subjects | HIGH |
| 3 | Agentic Proactive Behavior | Bot only answers — doesn't guide, plan, ask clarifying questions, or suggest follow-ups | HIGH |
| 4 | Model Preloading at Startup | CrossEncoder loads on first request — 3–5s delay for every cold start | MEDIUM |

---

## Upgrade 1 — MongoDB Integration

### Why MongoDB

Right now document metadata lives in a flat `metadata.json` file. This works for 5 PDFs. At 50+ PDFs or when you need to delete one specific document's chunks from FAISS, JSON breaks completely.

MongoDB gives you:
- Per-document chunk queries — find all chunks from one PDF instantly
- Fast delete — remove all chunks for a document with one query
- Filtering by subject/semester before retrieval
- Compound index on `(doc_id, chunk_id)` — sub-millisecond lookup

### MongoDB Document Schema

```python
# MongoDB collection: woxbot.chunks
{
  "_id": ObjectId(),
  "doc_id": "sha256-hash-of-pdf",          # links to documents collection
  "chunk_index": 0,                         # position within document
  "filename": "OS_Unit3_Notes.pdf",
  "subject": "Operating Systems",           # extracted from filename or user input
  "semester": 3,                            # user provides on upload
  "doc_type": "notes",                      # notes | syllabus | lab_manual | paper
  "section_title": "Round Robin Scheduling",
  "page": 12,
  "text": "...",
  "embedding_model_version": "text-embedding-004",
  "faiss_index": 4821,                      # position in FAISS flat index
  "created_at": ISODate("2026-03-01")
}

# MongoDB collection: woxbot.documents
{
  "_id": "sha256-hash",
  "filename": "OS_Unit3_Notes.pdf",
  "subject": "Operating Systems",
  "semester": 3,
  "doc_type": "notes",
  "chunk_count": 47,
  "pages": 24,
  "scanned_pages": [3, 7],
  "summary": "...",                         # auto-generated on upload (Upgrade 3)
  "uploaded_at": ISODate("2026-03-01"),
  "status": "indexed"                       # indexed | processing | failed
}
```

### Files to Create or Modify

| File | Action | What Changes |
|---|---|---|
| `backend/app/db/mongo.py` | CREATE | MongoDB connection using `motor` (async). Singleton pattern. |
| `backend/app/db/chunk_store.py` | CREATE | `save_chunks()`, `get_chunks_by_doc()`, `delete_chunks_by_doc()`, `filter_chunks()` |
| `backend/app/ingestion/embedder.py` | MODIFY | After FAISS insert → write chunks to MongoDB instead of `metadata.json` |
| `backend/app/api/routes/ingest.py` | MODIFY | Save document record to `woxbot.documents` on successful ingest |
| `backend/app/api/routes/sources.py` | MODIFY | Read from MongoDB. DELETE removes from FAISS + BM25 + MongoDB atomically |
| `backend/.env` | MODIFY | Add `MONGODB_URI` and `MONGODB_DB` |
| `backend/requirements.txt` | MODIFY | Add `motor>=3.3.1` and `pymongo>=4.6.0` |

### Implementation

**`backend/app/db/mongo.py`**
```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

_client: AsyncIOMotorClient = None

async def connect_db():
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    await _client.admin.command("ping")
    print("[MongoDB] Connected")

async def get_db():
    return _client[settings.MONGODB_DB]
```

**`backend/app/db/chunk_store.py`**
```python
from app.db.mongo import get_db

async def save_chunks(chunks: list[dict]):
    db = await get_db()
    if chunks:
        await db.chunks.insert_many(chunks)

async def get_chunks_for_docs(doc_ids: list[str]) -> list[dict]:
    """Fetch all chunks for selected documents — used in multi-doc filtering."""
    db = await get_db()
    cursor = db.chunks.find({"doc_id": {"$in": doc_ids}})
    return await cursor.to_list(length=None)

async def delete_chunks_by_doc(doc_id: str) -> int:
    db = await get_db()
    result = await db.chunks.delete_many({"doc_id": doc_id})
    return result.deleted_count

async def list_documents() -> list[dict]:
    db = await get_db()
    cursor = db.documents.find({}, {"_id": 1, "filename": 1, "subject": 1,
                                     "semester": 1, "chunk_count": 1, "uploaded_at": 1})
    return await cursor.to_list(length=None)
```

### Docker Setup for MongoDB (Local Dev)

```yaml
# Add to docker-compose.yml
services:
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

volumes:
  mongodb_data:
```

```bash
docker-compose up -d mongodb

# Verify connection:
python -c "from pymongo import MongoClient; c = MongoClient(); print(c.admin.command('ping'))"
```

### ⚠️ Migration Step

After adding MongoDB, run a one-time migration to import existing `metadata.json` into MongoDB. Then rename `metadata.json` → `metadata.json.bak`. Only delete it after confirming MongoDB queries return correct data.

```python
# run_migration.py (one-time script)
import json, asyncio
from app.db.mongo import connect_db, get_db

async def migrate():
    await connect_db()
    db = await get_db()
    with open("vector_db/metadata.json") as f:
        chunks = json.load(f)
    await db.chunks.insert_many(chunks)
    print(f"Migrated {len(chunks)} chunks to MongoDB")

asyncio.run(migrate())
```

---

## Upgrade 2 — Multi-Document Selection

### How It Works

Student uploads 5 PDFs (OS notes, DBMS notes, Maths syllabus, etc.). Before chatting, they see a document picker. They select only the 2 OS docs. WoxBot searches ONLY those — faster and more accurate.

**Student flow:**
1. Upload PDFs → each gets indexed and stored in MongoDB
2. Sidebar shows a checkbox panel: all uploaded docs
3. Student checks: `[✓] OS_Unit3_Notes.pdf` `[✓] OS_Syllabus.pdf` `[ ] DBMS_notes.pdf`
4. Student asks: *"What are the scheduling algorithms?"*
5. WoxBot retrieves from selected docs only

### Backend Changes

**Update `backend/app/api/schemas.py`**
```python
class ChatRequest(BaseModel):
    query: str
    session_id: str
    selected_doc_ids: list[str] = []   # NEW — empty = search all docs (backward compatible)
```

**Update `backend/app/retrieval/retriever.py`**
```python
async def hybrid_retrieve(query: str, selected_doc_ids: list[str] = []) -> list[dict]:
    query_vec = await embed(query)
    query_tokens = tokenize(query)

    if selected_doc_ids:
        # Get FAISS index positions for selected docs from MongoDB
        allowed_indices = await get_faiss_indices_for_docs(selected_doc_ids)
        faiss_results = faiss_search_filtered(query_vec, allowed_indices, top_k=20)
        bm25_results = bm25_search_filtered(query_tokens, selected_doc_ids, top_k=20)
    else:
        # Original behavior — search everything
        faiss_results = faiss_search(query_vec, top_k=20)
        bm25_results = bm25_search(query_tokens, top_k=20)

    # RRF fusion + CrossEncoder reranker — unchanged
    return rrf_fuse_and_rerank(faiss_results, bm25_results)
```

**FAISS Filtered Search**
```python
import numpy as np
import faiss

def faiss_search_filtered(query_vec: np.ndarray, allowed_indices: list[int], top_k: int):
    """FAISS doesn't natively filter — use IDSelectorBatch (requires faiss >= 1.7.3)"""
    selector = faiss.IDSelectorBatch(np.array(allowed_indices, dtype=np.int64))
    search_params = faiss.SearchParametersIVF(sel=selector)
    scores, indices = index.search(
        np.array([query_vec], dtype=np.float32),
        top_k,
        params=search_params
    )
    return scores[0], indices[0]
```

### New API Endpoints

| Method | Endpoint | Returns |
|---|---|---|
| `GET` | `/api/documents` | All indexed docs: id, filename, subject, semester, chunk_count, uploaded_at |
| `GET` | `/api/documents/{doc_id}/summary` | Auto-generated summary for that document |
| `DELETE` | `/api/documents/{doc_id}` | Remove doc from FAISS + BM25 + MongoDB atomically |

### Frontend Changes

**New component: `src/components/DocumentSelector.jsx`**
```jsx
export function DocumentSelector({ documents, selectedIds, onToggle }) {
  return (
    <div className="doc-selector">
      <p className="selector-label text-xs font-semibold text-slate-400 mb-2">
        Search in:
      </p>
      {documents.map(doc => (
        <label key={doc.id} className="doc-item flex items-center gap-2 mb-1 cursor-pointer">
          <input
            type="checkbox"
            checked={selectedIds.includes(doc.id)}
            onChange={() => onToggle(doc.id)}
            className="rounded"
          />
          <span className="doc-name text-sm text-slate-200 truncate">{doc.filename}</span>
          <span className="doc-meta text-xs text-slate-500">{doc.chunk_count} chunks</span>
        </label>
      ))}
      {selectedIds.length === 0 && (
        <p className="text-xs text-slate-500 italic mt-1">Searching all documents</p>
      )}
    </div>
  )
}
```

**Update `hooks/useChat.js`**
```javascript
const [selectedDocIds, setSelectedDocIds] = useState([]);

const sendMessage = async (query) => {
  await streamChat({
    query,
    session_id: sessionId,
    selected_doc_ids: selectedDocIds    // pass to backend
  });
};
```

---

## Upgrade 3 — Agentic Proactive Behavior

### What Changes

WoxBot currently only reacts. A real agentic assistant proactively:
- Asks ONE clarifying question when the query is vague
- Auto-summarizes each uploaded PDF and suggests questions
- Detects study/exam intent and builds a structured plan
- Sends 3 follow-up question suggestions after every answer

### 3a — Clarify Node (was a stub in Phase 4 — now fully implement)

**`backend/app/agent/nodes.py` — add clarify_node**
```python
CLARIFY_PROMPT = """
You are WoxBot. The student's question is vague or too broad to answer from documents.
Ask ONE specific clarifying question to understand what they need.

Available documents: {doc_list}
Student asked: {query}

Rules:
- Ask ONLY ONE question — never two
- Make it specific (not generic "can you clarify?")
- Offer 2–3 example options in your question if helpful
- Never say "I don't understand"
- Keep it under 2 sentences
"""

async def clarify_node(state: AgentState) -> AgentState:
    doc_list = ", ".join(state["available_docs"])
    prompt = CLARIFY_PROMPT.format(doc_list=doc_list, query=state["rewritten_query"])
    question = await llm.agenerate(prompt)
    state["response"] = question
    state["needs_clarification"] = True
    return state
```

### 3b — Auto-Summary on Document Upload

When a PDF is ingested, automatically generate a summary and store it in MongoDB. Show it instantly in the UI.

**`backend/app/ingestion/summarizer.py`** (CREATE NEW)
```python
AUTO_SUMMARY_PROMPT = """
You are WoxBot. A student just uploaded a document.
Based on the content below, provide:

## What This Document Contains
- Subject and main topics covered
- Key chapters or units (list them)
- Type: notes / syllabus / lab manual / question paper

## 3 Questions You Can Ask Me About This Document
List 3 specific, useful questions this document can answer.

Keep the summary concise. Use bullet points.

Document content (first 10 chunks):
{sample_chunks}
"""

async def generate_doc_summary(doc_id: str, chunks: list[dict]) -> str:
    sample_text = "\n\n".join([c["text"] for c in chunks[:10]])
    prompt = AUTO_SUMMARY_PROMPT.format(sample_chunks=sample_text)
    summary = await llm.agenerate(prompt)
    # Save to MongoDB
    db = await get_db()
    await db.documents.update_one({"_id": doc_id}, {"$set": {"summary": summary}})
    return summary
```

**In `backend/app/api/routes/ingest.py`** — call after successful FAISS indexing:
```python
# After ingestion completes:
summary = await generate_doc_summary(doc_id, chunks)
return IngestResponse(
    doc_id=doc_id,
    chunk_count=len(chunks),
    summary=summary          # send back to frontend to display immediately
)
```

### 3c — Study Planner Node

**Update keyword pre-router in `backend/app/agent/router.py`:**
```python
study_keywords = [
    "exam", "study plan", "prepare", "revision", "help me study",
    "tomorrow exam", "last minute", "important topics", "what to study"
]
if any(k in q for k in study_keywords):
    return "study_planner"
```

**Add study_planner node in `nodes.py`:**
```python
STUDY_PLAN_PROMPT = """
You are WoxBot, an academic advisor for Woxsen University.
Student query: {query}
Available documents and their summaries:
{doc_summaries}

Create a structured study plan using ONLY the uploaded documents:

## Study Plan
### High Priority Topics (must know)
### Suggested Study Order
### Time Estimate per Topic
### Key Concepts to Review
### 5 Practice Questions from Your Notes

Use bullet points and tables. Be specific — reference actual topics from the documents.
"""

async def study_planner_node(state: AgentState) -> AgentState:
    # Fetch summaries from MongoDB for selected docs
    summaries = await get_doc_summaries(state["selected_doc_ids"])
    doc_summaries = "\n\n".join([f"**{s['filename']}**:\n{s['summary']}" for s in summaries])
    prompt = STUDY_PLAN_PROMPT.format(
        query=state["rewritten_query"],
        doc_summaries=doc_summaries
    )
    plan = await llm.agenerate(prompt)
    state["response"] = plan
    return state
```

### 3d — Follow-Up Question Suggestions

After every answer, generate 3 follow-up questions. Send as a new SSE event.

**`backend/app/generation/followups.py`** (CREATE NEW)
```python
FOLLOWUP_PROMPT = """
Based on this Q&A exchange, suggest 3 natural follow-up questions a student might ask.
Make them specific and answerable from the same documents.

Original question: {query}
Answer summary: {answer_summary}

Return ONLY a JSON array of 3 strings. No preamble. Example:
["What are the advantages of Round Robin?", "How does quantum size affect performance?", "Compare Round Robin with FCFS"]
"""

async def generate_followups(query: str, answer: str) -> list[str]:
    answer_summary = answer[:500]   # first 500 chars as context
    prompt = FOLLOWUP_PROMPT.format(query=query, answer_summary=answer_summary)
    raw = await llm.agenerate(prompt)
    try:
        return json.loads(raw.strip())
    except Exception:
        return []   # fail silently — follow-ups are optional
```

**Update SSE stream in `backend/app/api/routes/chat.py`:**
```python
async def generate_stream(query: str, session_id: str, selected_doc_ids: list[str]):
    answer_tokens = []

    async for token in agent.stream(query, session_id, selected_doc_ids):
        answer_tokens.append(token)
        yield f"data: {token}\n\n"

    sources = agent.get_last_sources(session_id)
    yield f"data: [SOURCES_START]\n\n"
    yield f"data: {json.dumps({'chunks': sources})}\n\n"

    # NEW: follow-up suggestions
    followups = await generate_followups(query, "".join(answer_tokens))
    if followups:
        yield f"data: [FOLLOWUPS_START]\n\n"
        yield f"data: {json.dumps({'questions': followups})}\n\n"

    yield f"data: [DONE]\n\n"
```

**Update `hooks/useStream.js` to handle `[FOLLOWUPS_START]`:**
```javascript
// In your SSE onmessage handler — add this block alongside [SOURCES_START] handling:
if (data === "[FOLLOWUPS_START]") {
  parsingFollowups = true;
  return;
}
if (parsingFollowups) {
  const parsed = JSON.parse(data);
  setFollowupQuestions(parsed.questions);
  parsingFollowups = false;
  return;
}
```

**Show follow-up buttons below each bot message in `MessageBubble.jsx`:**
```jsx
{isBot && followupQuestions?.length > 0 && (
  <div className="followup-suggestions mt-3 flex flex-wrap gap-2">
    {followupQuestions.map((q, i) => (
      <button
        key={i}
        onClick={() => onFollowupClick(q)}
        className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1 rounded-full border border-slate-600"
      >
        {q}
      </button>
    ))}
  </div>
)}
```

### Updated LangGraph Flow

```
START
  → [Query Rewriter]            converts vague follow-ups → standalone query
  → [Keyword Pre-Router]        rule-based fast routing (no LLM cost)
      ├── document_qa   → [RAG Node] → Filtered Retrieval → Reranker(8) → LLM → Sources
      ├── web_search    → [Search Node] → DuckDuckGo → LLM
      ├── calculation   → [Calculator Node] → pure float arithmetic
      ├── summarize     → [Summarizer Node] → map-reduce chunks → LLM
      ├── study_planner → [Study Plan Node] → MongoDB doc summaries → LLM plan
      └── unclear       → [Clarify Node] → ONE clarifying question → wait for user
  → [Follow-Up Generator]       always runs after any answer
  → [Memory Node]               save turn to 5-turn buffer
  → [Stream Node]               SSE: tokens → [SOURCES_START] → [FOLLOWUPS_START] → [DONE]
END
```

---

## Upgrade 4 — Model Preloading at Startup

### The Problem

CrossEncoder, FAISS index, and BM25 all load lazily on the first request. Every Render.com redeploy or sleep-wake cycle means the first student waits 3–5 seconds. Fix: load everything during `lifespan()` startup.

### Implementation

**`backend/app/main.py` — replace `@app.on_event("startup")` with lifespan:**
```python
from contextlib import asynccontextmanager
from app.retrieval.reranker import load_reranker
from app.retrieval.vector_store import load_faiss_index
from app.retrieval.bm25_store import load_bm25_index
from app.generation.llm import warm_up_llm
from app.db.mongo import connect_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Loading all models and indexes...")

    await connect_db()
    print("[Startup] ✓ MongoDB connected")

    await load_faiss_index()
    print("[Startup] ✓ FAISS index loaded")

    await load_bm25_index()
    print("[Startup] ✓ BM25 index loaded")

    await load_reranker()
    print("[Startup] ✓ CrossEncoder loaded")

    await warm_up_llm()
    print("[Startup] ✓ LLM warmed up")

    print("[Startup] All systems ready. First request will be fast.")
    yield
    # Shutdown
    print("[Shutdown] Cleaning up...")

app = FastAPI(lifespan=lifespan)
```

### Singleton Pattern for All Models

Use module-level singletons — load once, reuse across all requests.

**`backend/app/retrieval/reranker.py`**
```python
_reranker = None   # module-level singleton

async def load_reranker():
    global _reranker
    from sentence_transformers import CrossEncoder
    _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    # Warm-up run — prevents cold inference delay on first real request
    _reranker.predict([("test query", "test passage")])
    print("[Reranker] Model warmed up")

def get_reranker():
    if _reranker is None:
        raise RuntimeError("Reranker not loaded. Check lifespan().")
    return _reranker
```

**`backend/app/retrieval/vector_store.py`**
```python
_index = None

async def load_faiss_index():
    global _index
    import faiss
    _index = faiss.read_index(settings.VECTOR_DB_PATH + "/faiss.index")

def get_index():
    return _index
```

### LLM Warm-Up

```python
# backend/app/generation/llm.py

async def warm_up_llm():
    """Pre-initialize API connection pool at startup."""
    try:
        await generate("ping", system="Reply with: pong", max_tokens=5)
        print("[LLM] Warm-up successful")
    except Exception as e:
        # NEVER crash startup if warm-up fails — just log it
        print(f"[LLM] Warm-up skipped: {e}")
```

### Render.com Keep-Alive (Prevents Cold Starts)

Render free tier spins down after 15 minutes of inactivity. Add a self-ping task:

```python
# backend/app/utils/keep_alive.py
import asyncio
import httpx

async def keep_alive_ping(url: str, interval_seconds: int = 600):
    """Ping /api/health every 10 minutes to prevent Render sleep."""
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                await client.get(f"{url}/api/health")
            except Exception:
                pass

# In lifespan(), before yield:
# import asyncio
# asyncio.create_task(keep_alive_ping(settings.BACKEND_URL))
```

---

## Formatting Fix — Bold Text Not Rendering

If `**bold**` appears as raw asterisks, the cause is Tailwind's CSS preflight reset overriding react-markdown output.

### Fix 1 — Install remark-gfm (required for tables)

```bash
npm install react-markdown remark-gfm
```

### Fix 2 — MessageBubble.jsx (complete replacement)

```jsx
// src/components/MessageBubble.jsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function MessageBubble({ message }) {
  const isBot = message.role === 'assistant'

  return (
    <div className={isBot ? 'bot-bubble' : 'user-bubble'}>
      {isBot ? (
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
      ) : (
        <p>{message.content}</p>
      )}
    </div>
  )
}
```

### Fix 3 — globals.css (add !important overrides)

Tailwind's preflight resets `font-weight`, `list-style`, and margins to `none`. The `!important` below is **required** — without it bold and bullets will not appear even with react-markdown installed.

```css
/* Add to src/styles/globals.css */

.bot-bubble { line-height: 1.6; }

/* Bold — !important required to override Tailwind preflight */
.bot-bubble strong,
.bot-bubble b {
  font-weight: 700 !important;
  color: #60a5fa;
}

.bot-bubble em { font-style: italic !important; color: #a5b4fc; }

/* Headings */
.bot-bubble h2 { font-size: 1.2rem; font-weight: 700; margin: 14px 0 8px; color: #e2e8f0; }
.bot-bubble h3 { font-size: 1rem; font-weight: 600; margin: 10px 0 6px; color: #cbd5e1; }

/* Lists — !important required to override Tailwind preflight */
.bot-bubble ul { list-style: disc !important; padding-left: 20px !important; margin: 8px 0; }
.bot-bubble ol { list-style: decimal !important; padding-left: 20px !important; margin: 8px 0; }
.bot-bubble li { margin: 4px 0; }

/* Tables */
.bot-bubble table { width: 100%; border-collapse: collapse; margin: 12px 0; }
.bot-bubble th { background: #1e3a5f; color: white; padding: 8px 12px; font-weight: 700; text-align: left; }
.bot-bubble td { border: 1px solid #374151; padding: 8px 12px; }
.bot-bubble tr:nth-child(even) td { background: #1e293b; }

/* Code */
.bot-bubble code { background: #1e293b; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.85em; }
.bot-bubble pre { background: #1e293b; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
.bot-bubble pre code { background: transparent; padding: 0; }
```

---

## Updated System Prompt (prompt.py)

Replace your existing `SYSTEM_PROMPT` with this. The formatting rules are what force the LLM to use markdown structure instead of plain paragraphs.

```python
# backend/app/generation/prompt.py

SYSTEM_PROMPT = """
You are WoxBot, an academic assistant for Woxsen University students.

STRICT RULES:
1. Answer ONLY using the context provided below.
2. NEVER use outside knowledge for factual answers.
3. If the answer is not in the context, respond exactly:
   "I couldn't find this in your uploaded documents. Please upload the relevant notes."
4. Do NOT include [Source: filename, Page X] inline — sources are attached automatically.
5. Do NOT make up page numbers, filenames, or any fact not in the context.

FORMATTING RULES — FOLLOW EXACTLY:
6. NEVER respond in plain paragraphs. Always use structured markdown.
7. Use ## for main topics, ### for subtopics.
8. Use bullet points ( - ) for lists of features, properties, or items.
9. Use numbered lists ( 1. 2. 3. ) for steps, procedures, or sequences.
10. Use **bold** to highlight key terms, definitions, and important values.
11. Use markdown tables when comparing items or showing data with categories.
12. Use `code blocks` for code snippets, commands, or syntax.
13. End EVERY response with a ### Summary section — 2–3 lines max.
14. If the answer has more than 3 points — use a table or bullet list, NEVER a paragraph.

CONTEXT:
{retrieved_chunks}

CONVERSATION HISTORY:
{memory}

STUDENT QUESTION:
{query}
"""

FORMATTING_EXAMPLE = """
Example of correct response format:

Question: What is Round Robin Scheduling?

## Round Robin Scheduling

**Definition:** A CPU scheduling algorithm where each process gets a fixed time slice called a **quantum**.

### Key Properties

| Property | Value |
|---|---|
| Type | Preemptive |
| Starvation | No starvation possible |
| Best For | Time-sharing systems |

### How It Works

1. All processes placed in a **circular queue**
2. Each process runs for exactly **one quantum**
3. If not finished, moves to the **back of the queue**

### Summary
Round Robin is a preemptive scheduling algorithm using a fixed time quantum. It ensures fairness but has overhead from frequent context switches.
"""

def build_prompt(query: str, retrieved_chunks: str, memory: str) -> str:
    return f"""
{SYSTEM_PROMPT}

{FORMATTING_EXAMPLE}

CONTEXT:
{retrieved_chunks}

CONVERSATION HISTORY:
{memory}

STUDENT QUESTION:
{query}

Respond using proper markdown formatting as shown in the example above.
"""
```

---

## Updated .env

```bash
# backend/.env — full updated version

# LLM Providers
GEMINI_API_KEY=your_key
GROK_API_KEY=your_key
OPENROUTER_API_KEY=your_key
LOCAL_PHI3_URL=http://localhost:11434
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_LLM_MODEL=gemini-1.5-flash

# MongoDB (NEW)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=woxbot

# Retrieval
CHUNK_SIZE=400
CHUNK_OVERLAP=80
RERANK_TOP_K=8
RETRIEVAL_TOP_K=20
EMBEDDING_MODEL_VERSION=text-embedding-004

# Agent
MAX_MEMORY_TURNS=5
GENERATE_FOLLOWUPS=true
AUTO_SUMMARIZE_ON_UPLOAD=true

# Paths
VECTOR_DB_PATH=./vector_db
DATA_RAW_PATH=./data/raw

# Deploy
BACKEND_URL=http://localhost:8000
LOG_LEVEL=INFO
```

---

## Implementation Order

Do these in order. Each builds on the previous.

| # | Task | Time | Done When |
|---|---|---|---|
| 1 | **Formatting fix** — install `remark-gfm`, add `!important` CSS overrides | 30 min | Bold renders in blue. Tables display. Bullets appear. |
| 2 | **MongoDB** — install motor, create `mongo.py` + `chunk_store.py`, migrate `metadata.json` | 3 hrs | Chunks queryable by `doc_id`. Delete works cleanly. |
| 3 | **Model preloading** — add `lifespan()`, singleton pattern for all models | 1 hr | Server logs "All systems ready" at startup. First request < 1s. |
| 4 | **Multi-doc selection** — update `ChatRequest`, filtered retrieval, `DocumentSelector.jsx` | 4 hrs | Checkboxes work. Retrieval only pulls from selected docs. |
| 5 | **Auto-summary on upload** — `summarizer.py`, show in UI after ingest | 2 hrs | Upload PDF → bot shows summary + 3 suggested questions. |
| 6 | **Clarify node + Study Planner** — implement nodes, update LangGraph edges | 3 hrs | Vague queries get one clarifying question. Exam queries return study plan. |
| 7 | **Follow-up suggestions** — `[FOLLOWUPS_START]` SSE event, clickable buttons | 2 hrs | 3 follow-up question buttons appear below each answer. Clicking runs them. |

---

## ✅ Done When (Phase 8 Complete)

- [ ] Bold text renders in blue, bullet points visible, tables display correctly
- [ ] All document metadata lives in MongoDB — `metadata.json` deprecated
- [ ] Student can select 2 of 5 uploaded PDFs and retrieval is scoped to those only
- [ ] First request after server start responds in under 1 second
- [ ] Uploading a PDF auto-generates a summary with 3 suggested questions
- [ ] Typing "help me study for OS exam" returns a structured study plan
- [ ] Vague queries like "explain it" trigger one clarifying question
- [ ] Every bot answer ends with 3 clickable follow-up question buttons

---

*WoxBot — Phase 8 · Dara Eakeswar Rayudu · Woxsen University · March 2026*.py — send raw text tokens, then one JSON block for sources
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
