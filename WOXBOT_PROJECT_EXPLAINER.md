# WoxBot — What We Built, Why We Built It, and How It Works

> *A plain-English breakdown for teammates, friends, and anyone curious about the project.*

---

## The Big Idea — What Problem Are We Solving?

Every student at Woxsen has been through this: your exam is tomorrow, you have a 120-page syllabus PDF, three lab manuals, and a bunch of lecture notes downloaded from the portal. You need to quickly find *"what are the topics in Unit 4?"* or *"what is the difference between TCP and UDP according to my notes?"* — and instead of getting a fast answer, you're spending 20 minutes scrolling through files.

**WoxBot fixes that.**

You upload your PDFs once. Then you just ask questions in plain English, and the bot answers using your own documents — not random internet knowledge, not hallucinated facts, but your actual syllabus and notes. It tells you exactly which page and section the answer came from. It can even build you a study plan, calculate your CGPA, and suggest follow-up questions you should be asking.

That's the core idea: **your documents, your questions, instant answers**.

---

## What WoxBot Can Do (Features Explained Simply)

| What You Do | What WoxBot Does |
|---|---|
| Upload a PDF (syllabus, notes, lab manual) | Reads it, breaks it into smart chunks, indexes it for fast search |
| Ask "What is covered in Unit 3?" | Searches your documents, finds the right sections, generates a clear answer |
| Ask "Calculate my CGPA: 8.2, 7.9, 8.5, 9.0" | Directly computes it — no document needed |
| Ask "What's the latest news about AI?" | Searches the web (DuckDuckGo) and gives you a summary |
| Ask "Make me a study plan for tomorrow's exam" | Reads all your uploaded docs and builds a structured plan with priorities |
| Ask a vague question | Asks you one smart clarifying question instead of guessing wrong |
| Read the answer | Sees formatted text — headings, bullet points, code blocks, tables |
| Click a source badge | Sees which page and section the answer was pulled from |
| Click a follow-up button | Sends a suggested next question in one click |
| Switch from Groq to Gemini | The same system works with a different AI brain — just pick from the dropdown |

---

## The Tech Stack — What We Used and Why

This is the most important part. Every tool we picked was a deliberate choice. Here's the reasoning behind each one.

---

### Frontend: React 19 + Vite + Tailwind CSS

**What it is:** React is the JavaScript framework for building the user interface. Vite is the build tool. Tailwind is the CSS library.

**Why React 19 specifically?**
React 19 introduced major performance improvements and concurrent rendering features. Since our chat interface streams tokens in real time (the answer appears word-by-word like ChatGPT), we need the UI to update hundreds of times per second without freezing. React 19 handles this smoothly.

**Why Vite instead of Create React App or Webpack?**
Vite is dramatically faster at development. When you save a file, the page reloads in under 100ms. With Webpack-based setups, you'd wait 2–5 seconds. Vite uses ES modules natively in the browser during dev, so there's no bundling step — it's instant.

**Why Tailwind CSS instead of plain CSS or Bootstrap?**
Tailwind lets you write styles directly on the element (like `className="bg-zinc-900 text-white rounded-lg p-4"`) instead of jumping between CSS files. This keeps everything in one place. For a chat UI with lots of small components, this is much faster to build and iterate on. We used the **zinc** color family throughout for a consistent, neutral look that works in both dark and light mode.

**Why react-markdown + remark-gfm?**
The AI generates answers with formatting — bold text, bullet points, numbered lists, code blocks. If we just displayed the raw text, you'd see `**bold**` and `- item` instead of actual formatting. `react-markdown` renders the markdown syntax into HTML. `remark-gfm` adds support for GitHub-flavored tables, strikethrough, and task lists.

---

### Backend: FastAPI + Python 3.12

**What it is:** FastAPI is the web framework. Python is the language for all AI/ML processing.

**Why FastAPI over Flask or Django?**
Three reasons:
1. **Speed** — FastAPI is built on ASGI (async), meaning it can handle hundreds of concurrent requests without blocking. Flask is synchronous — one request blocks others. For a chat app where multiple users might be streaming responses at the same time, async is essential.
2. **Auto validation** — FastAPI uses Pydantic models, so if you send wrong data to an API endpoint, it automatically returns a clear error. No manual validation code needed.
3. **Auto docs** — FastAPI generates interactive API documentation at `/docs` automatically. Huge time-saver for development.

**Why Python?**
Simple: the best AI/ML libraries (FAISS, sentence-transformers, LangGraph, PyMuPDF) are Python-first. There's no real alternative for what we're doing.

**Why Python 3.12?**
Performance improvements over 3.10/3.11 — Python 3.12 is about 5% faster overall and has better error messages during development.

---

### Streaming: Server-Sent Events (SSE)

**What it is:** A way for the server to continuously push data to the browser over a single HTTP connection.

**Why SSE instead of WebSockets?**
WebSockets are bidirectional (browser and server can both send data). SSE is one-directional (server → browser only). For a chatbot, the browser sends one message and the server streams back the response — that's perfectly one-directional.

**The advantage of SSE:**
- Simpler to implement (it's just HTTP, no upgrade handshake)
- Works through CDNs and proxies without special configuration
- Built into browsers natively — no library needed on the frontend
- Automatic reconnection if the connection drops

The user sees the answer appearing word-by-word (exactly like ChatGPT), which feels much more responsive than waiting 5 seconds for the entire answer to appear at once.

---

### PDF Processing: PyMuPDF (fitz)

**What it is:** A Python library for reading PDFs.

**Why PyMuPDF over pdfplumber or pypdf?**
PyMuPDF is the fastest Python PDF library by a significant margin — it processes a 100-page PDF in under a second. It's also more accurate with complex layouts (multi-column text, tables like those in lab manuals). It can detect scanned pages (images disguised as text) by checking if a page has less than 50 characters, which is important for flagging PDFs that need OCR.

---

### Smart Chunking: Section-Aware Chunker (Custom)

**What it is:** The process of breaking a PDF into smaller pieces so the AI can search through them.

**Why not just cut every 500 words?**
This is a critical design decision. Imagine your OS syllabus has Unit 1, Unit 2, Unit 3. If you blindly cut every 500 characters, you'd get chunks that start in the middle of Unit 1 and end in the middle of Unit 2 — the chunk has no idea which unit it belongs to. When a student asks "What's in Unit 3?", the AI might pull the wrong chunk.

**Our approach:** We detect headings first (using patterns for ALL CAPS lines, Title Case lines, numbered sections like "1.2.3", "Chapter 2"). We split at heading boundaries — each chunk belongs to exactly one section. Then we apply the 400-token size limit *within* each section. Every chunk starts with its section title as context.

**Result:** When the AI retrieves a chunk about process scheduling, it also sees `[1.2 Process Scheduling]` as context. The answers are much more precisely grounded.

---

### Embeddings: text-embedding-3-small (OpenRouter)

**What it is:** Converting text into a list of 1536 numbers (a vector) that captures the *meaning* of the text.

**Why embeddings?**
Words alone can't capture meaning. "Car" and "automobile" have zero word overlap but mean the same thing. "Bank" can mean a financial institution or a river bank — same word, different meaning. Embeddings encode semantic meaning — similar concepts end up with similar vectors regardless of exact wording.

**Why text-embedding-3-small specifically?**
It's OpenAI's second-generation embedding model. 1536 dimensions gives a good balance between accuracy and speed/cost. It understands academic English well. The "small" version is 5× cheaper than `text-embedding-3-large` with only a small accuracy drop — fine for our use case.

**Why through OpenRouter?**
OpenRouter is an API aggregator that gives access to many AI models through one API key. This means we can switch embedding models later without changing code.

---

### Vector Search: FAISS (Facebook AI Similarity Search)

**What it is:** A library that stores millions of vectors and finds the most similar ones to a query in milliseconds.

**Why FAISS?**
When a student asks a question, we embed their question into a vector, then need to find the 20 most similar chunk vectors out of potentially thousands. Doing this naively (comparing against every chunk) takes too long. FAISS uses optimized index structures to do this search in milliseconds even with millions of vectors.

**Why IndexFlatIP (Inner Product)?**
We L2-normalize all vectors before storing them. On normalized vectors, inner product = cosine similarity. Cosine similarity measures the *angle* between two vectors — a better measure of semantic relatedness than raw distance. A chunk can be long and a query can be short, but if they're about the same topic, their cosine similarity is high.

**Why store it on disk (faiss.index file)?**
So the index persists between server restarts. Without this, you'd have to re-embed all documents every time you restarted the server — which might take 5–10 minutes with many PDFs.

---

### Keyword Search: BM25 (Best Match 25)

**What it is:** A classic algorithm that finds documents containing the query words, weighted by how unusual those words are.

**Why BM25 in addition to FAISS?**
FAISS finds *semantically similar* text — great for paraphrased questions. But it sometimes misses exact matches for specific terms: course codes, formula names, professor surnames, acronyms. BM25 excels at exact keyword matching. Combining both gives us the best of both worlds.

**Why BM25Okapi specifically?**
It's the most widely used variant of BM25. The "Okapi" refers to the library that standardized the formula. It handles term frequency saturation (a word appearing 100 times in a chunk doesn't make it 100× more relevant than appearing once) and document length normalization (short chunks aren't unfairly penalized).

**Why store as a pickle file?**
The BM25 index is just a Python object (tokenized corpus + statistics). Pickling it to disk is the simplest way to persist it. It loads in milliseconds.

---

### Fusion: Reciprocal Rank Fusion (RRF)

**What it is:** A mathematical formula for combining ranked lists from multiple search systems.

**Why not just pick the higher score?**
FAISS returns a cosine similarity score (0 to 1). BM25 returns a completely different score (can be 0 to 20+). They're not comparable — you can't directly say "FAISS score 0.8 > BM25 score 12." RRF solves this by converting both to *rank positions* (1st, 2nd, 3rd...) and combining them with the formula: `score = 1/(k + rank)` where k=60.

**Why this matters:**
A chunk that appears as #1 in FAISS and #3 in BM25 gets a much higher combined score than a chunk that appears #1 in FAISS but #100 in BM25. This automatically surfaces chunks that both systems agree are relevant.

---

### Reranker: CrossEncoder (ms-marco-MiniLM-L-6-v2)

**What it is:** A small AI model (22 million parameters) that scores how relevant a passage is to a query.

**Why do we need to rerank after FAISS + BM25?**
FAISS and BM25 are fast but imprecise. They look at the query and each chunk *separately*. A CrossEncoder looks at the (query, chunk) pair *together* — it understands the relationship between them. This is more accurate but too slow to run on thousands of chunks. So we use FAISS + BM25 to get a fast top-20 shortlist, then use CrossEncoder to precisely rank those 20 down to the best 8.

**Why this specific model?**
`ms-marco-MiniLM-L-6-v2` is trained on Microsoft's MS MARCO dataset — question-answer pairs from web search. It's well-optimized for query-passage relevance scoring. At 22M parameters, it runs in under 1 second for 20 passages on CPU, which is fast enough.

**Why load it at startup?**
The model takes 4–5 seconds to load from disk. If we loaded it on every request, the first few users would wait 5 extra seconds. By loading it at startup (before any requests arrive), all users get fast responses.

---

### AI Orchestration: LangGraph

**What it is:** A library for building AI agent pipelines as directed graphs.

**Why LangGraph instead of a simple if-else chain?**
A simple if-else chain becomes unmanageable with many routes. LangGraph lets us define the pipeline as a visual graph: nodes (pieces of logic) connected by edges (flow between them). Each node does one thing well. This makes it easy to add new nodes (we added `study_planner` later without touching other nodes), debug individual steps, and track state through the pipeline.

**Our 10-node graph:**
```
query → rewriter → router → [document_qa OR web_search OR calculator OR 
                              summarize OR clarify OR study_planner] 
                          → validator → memory → done
```

Every query flows through the same pipeline. The router decides which branch to take. This is called an **agentic architecture** — the system can *decide* what to do based on the input, rather than having a fixed hardcoded path.

**Why have a rewriter as the first node?**
If a student asks "What about Unit 3?" after asking about Unit 2, the word "that" or "it" doesn't mean anything without history. The rewriter node reads the last 5 messages and rewrites the query to be standalone: "What are the topics in Unit 3 of my OS syllabus?" — this makes retrieval much more accurate.

---

### LLM Providers: Groq + OpenRouter

**What they are:** APIs that give access to AI language models.

**Why multiple providers instead of just one?**
Different models have different strengths. Groq runs Llama 3.1 8B with extremely low latency (~200ms to first token). OpenRouter gives access to Gemini, DeepSeek, and other models. Different students might prefer different models for different tasks. We built a model selector in the frontend so the user can switch without any backend changes.

**Why Groq as the default?**
Groq uses custom hardware (LPUs — Language Processing Units) optimized specifically for running large language models. On the same Llama 3.1 8B model, Groq is 5–10× faster than other providers. For a chat app where speed matters, this makes a huge difference.

**Why OpenRouter for embeddings?**
OpenRouter gives access to OpenAI's embedding models without needing a direct OpenAI API key (which is harder to get and more expensive). `text-embedding-3-small` via OpenRouter costs $0.02 per 1M tokens — practically free for student usage.

---

### Database: MongoDB

**What it is:** A NoSQL document database.

**Why MongoDB for this project?**
Each uploaded document has a variable structure — different chunk counts, some have summaries, some don't yet. MongoDB's flexible document model handles this naturally without needing schema migrations like a SQL database would.

**Three collections we use:**
1. **documents** — one record per uploaded PDF (filename, hash, chunk count, auto-summary, upload date)
2. **chunks** — one record per text chunk (which doc it came from, which page, which section, the text itself)
3. **conversations** — conversation history per session (so memory persists even if you refresh the page)

**Why async MongoDB (motor)?**
`motor` is the async version of the MongoDB Python driver. Since our backend is fully async (FastAPI + ASGI), all database operations need to be async too — otherwise a slow DB query would block other users' requests.

---

### Hallucination Validation: 3-Tier Check

**What it is:** A system that checks whether the AI's answer is actually supported by the documents it retrieved.

**Why do we need this?**
Large language models sometimes "hallucinate" — they generate confident-sounding answers that aren't based on the retrieved documents. For an academic assistant where students rely on the information, we can't afford this.

**Our 3-tier approach (cheapest → most expensive):**

1. **Token overlap** (free, instant): Count what percentage of the answer's meaningful words also appear in the retrieved chunks. If 60%+ overlap → skip further checks, it's grounded. If less than 15% → it's hallucinated, add a disclaimer.

2. **Embedding similarity** (1 API call): If overlap is in the middle range (15–60%), embed the answer and compare it semantically to the chunk embeddings. We reuse the chunk embeddings already computed during source mapping — so this costs zero extra API calls in the common case.

3. **LLM judge** (1 LLM call, rare): Only for truly borderline cases (embedding similarity between 0.40–0.65). Send the question, answer, and context to the LLM and ask it to judge whether the answer is grounded. This is expensive (~$0.001) so we only run it when necessary.

**Result:** 90% of answers are validated for free. The user gets a ⚠️ disclaimer only when we actually detect potential hallucination.

---

### Auto-Summary on Upload

**What it is:** When you upload a PDF, WoxBot automatically generates a plain-English summary of what the document contains.

**Why?**
Students often upload a PDF and then don't know what questions to ask. The auto-summary tells them: *"This document covers Operating System process scheduling, memory management, and deadlock. You can ask me about: Which scheduling algorithms are covered? What is Banker's algorithm? How does virtual memory work?"*

It shows up as a toast notification right after upload — instant orientation to a new document.

---

### Follow-Up Suggestion Buttons

**What it is:** After every answer, 3 suggested follow-up questions appear as clickable buttons.

**Why?**
Research shows users often don't know how to continue a conversation with an AI after getting an answer. The follow-up buttons reduce friction — you don't have to think of the next question, you just click one that's already relevant.

---

### Multi-Document Selection

**What it is:** Checkboxes in the sidebar that let you pin specific documents for a query.

**Why?**
If you've uploaded 5 different PDFs and you only want to ask about your OS notes specifically (not your DBMS notes), you can pin just the OS document. The retrieval system then filters to only those chunks — you won't get irrelevant answers mixing different subjects.

---

### Study Planner Node

**What it is:** A dedicated AI mode triggered by phrases like "help me study", "exam tomorrow", "make a study plan".

**Why a separate node?**
Generic document Q&A isn't the right tool for "build me a study plan." The study planner reads the summaries of all your uploaded documents, understands what's in each one, and builds a structured plan with priorities, suggested study order, time estimates, key concepts to focus on, and 5 practice questions.

---

### API Security: X-API-Key + hmac.compare_digest()

**What it is:** A simple API key authentication system.

**Why hmac.compare_digest() instead of == for comparing keys?**
This is a security best practice. When you compare strings with `==`, Python returns `False` the moment it finds a character mismatch — which means comparing a key that starts with the right characters takes slightly longer than one that starts with wrong characters. An attacker can exploit this timing difference to guess the key one character at a time. `hmac.compare_digest()` always takes the same amount of time regardless, closing this side-channel.

---

### Deployment: Docker + Render.com

**Why Docker?**
Docker packages the entire application — Python version, dependencies, environment — into a container. This means: if it runs on your laptop, it runs exactly the same way on the server. No "works on my machine" problems.

**Why Render.com?**
It's a simple, developer-friendly cloud platform that deploys directly from a GitHub repository. Free tier available, automatic deploys on push, built-in SSL certificates. The `render.yaml` file in our repo describes everything Render needs to deploy the backend.

**Keep-alive ping:**
Render.com's free tier puts servers to sleep after 15 minutes of inactivity. We have a background task that pings the server's own `/api/health` endpoint every 10 minutes to keep it awake.

---

## How Everything Works Together — The Full Journey

Let's trace one complete student request from start to finish:

```
1. Student uploads "os_syllabus.pdf"

2. Backend saves the file → PyMuPDF reads it (5 pages, 0 scanned)

3. Section-aware chunker detects headings:
   "UNIT 1 — INTRODUCTION TO OS"
   "1.2 Process Scheduling"
   "UNIT 2 — MEMORY MANAGEMENT"
   → splits into 24 chunks, each with its section title

4. text-embedding-3-small converts each chunk into a 1536-number vector
   → stored in FAISS index on disk
   → also stored in BM25 index on disk
   → chunk metadata saved to MongoDB
   
5. LLM generates an auto-summary:
   "This document covers OS concepts including scheduling algorithms,
    memory management, and deadlock detection. You can ask:
    What is Round Robin scheduling? What is Banker's Algorithm?"
   → Toast notification appears in the UI

-------- Student asks: "explain banker's algorithm from my notes" --------

6. useStream.js sends POST /api/chat with the query

7. Query Rewriter: no history yet, query passes through unchanged

8. Keyword Router: detects "my notes" → routes to document_qa

9. Retrieval:
   - embed "explain banker's algorithm from my notes" → 1536-dim vector
   - FAISS finds top-20 semantically similar chunks
   - BM25 finds top-20 chunks containing "banker", "algorithm", "deadlock"
   - RRF fusion combines both lists → top-20 merged candidates
   - CrossEncoder scores each (query, chunk) pair → top-8 chunks

10. LLM (Groq, llama-3.1-8b-instant):
    Receives: system prompt + formatting rules + top-8 chunks + query
    Streams back answer token-by-token via SSE

11. Frontend (useStream.js) reads the stream:
    - Each token → React state update → MessageBubble re-renders
    - "[SOURCES_START]" → next event is JSON with source info
    - "[FOLLOWUPS_START]" → renders 3 clickable follow-up buttons
    - "[DONE]" → finalize message

12. Source mapping:
    - Answer is split into sentences
    - Each sentence is compared to the 8 chunks via cosine similarity
    - Best-matching chunk per sentence → source badge
    (shows "📄 os_syllabus.pdf — Page 7 — Deadlock Prevention")

13. Validation:
    - Token overlap: 52% → borderline, check embeddings
    - Embedding similarity: 0.71 → high confidence, no disclaimer needed

14. Follow-up generation (parallel):
    LLM generates: ["What is the safe state condition?",
                    "How does Banker's Algorithm prevent deadlock?",  
                    "What are the necessary conditions for deadlock?"]
    → Three clickable pill buttons appear below the answer

15. Conversation memory saved to MongoDB for next query context
```

---

## Numbers That Matter

| Metric | Value |
|---|---|
| First token latency (Groq) | ~200–400ms |
| PDF ingestion (10-page doc) | ~3–5 seconds |
| Chunks per typical 10-page syllabus | 20–30 chunks |
| CrossEncoder preload time (startup) | ~4–5 seconds (once, cached) |
| Embedding dimensions | 1536 |
| Context window per answer | 8 most relevant chunks |
| Conversation memory | Last 5 turns (configurable) |
| Validation: % of answers needing LLM judge | ~10% (borderline cases only) |
| Embedding API calls saved per answer | 1 (chunk_embs reused between source mapping and validation) |

---

## What Makes This Project Technically Impressive

1. **It's not just a wrapper around ChatGPT.** We built a full retrieval pipeline from scratch — chunking strategy, FAISS integration, BM25, RRF fusion, CrossEncoder reranking.

2. **The hallucination validator is novel.** Most RAG systems just trust the LLM. We actively check whether the answer is grounded in 3 tiers, cheapest first, reusing precomputed embeddings to avoid extra costs.

3. **The routing is smart.** A single question goes through a 2-tier routing system — deterministic keyword rules cover 90% of cases without ever hitting an LLM.

4. **Multi-document filtering is non-trivial.** FAISS doesn't support native ID filtering. We implemented over-retrieval (5× k) + post-filter as a workaround.

5. **The streaming SSE protocol is custom.** We designed a 3-marker protocol: regular tokens → `[SOURCES_START]` → `[FOLLOWUPS_START]` → `[DONE]`. The frontend state machine handles all three phases.

6. **The chunk embedding reuse.** Both source mapping and validation need chunk embeddings. We thread them through so one API call serves both — a non-obvious optimization that cuts answer latency by ~300ms.

---

## Summary

WoxBot is a full-stack AI application that combines a modern React frontend, a FastAPI async backend, a LangGraph agent pipeline, hybrid retrieval (FAISS + BM25 + CrossEncoder), multi-provider LLM support, and MongoDB — all working together to let students chat with their own academic documents.

Every technology choice was made deliberately: FastAPI for async performance, FAISS+BM25 for better retrieval than either alone, LangGraph for a maintainable agent architecture, Groq for low-latency inference, and SSE for real-time streaming without WebSocket complexity.

The result is a system that feels fast, gives sourced answers, doesn't hallucinate, and actually helps with the specific workflows students face before exams.

---

*WoxBot v1.0 — Built for Woxsen University Students*
