# WoxBot 🤖

**Agentic RAG Academic Assistant for Woxsen University**

A production-grade Retrieval-Augmented Generation chatbot with multi-LLM support, voice input, document management, and real-time SSE streaming.

**Stack:** React 19 + Vite + Tailwind CSS · FastAPI + Uvicorn · LangGraph · Groq / OpenRouter · FAISS + BM25 · Web Speech API

---

## Features

- **Multi-LLM Model Selector** — Switch between Groq (Llama, Mixtral, Gemma) and OpenRouter (DeepSeek, Qwen, Gemini) models from the navbar
- **SSE Streaming Chat** — Real-time token-by-token response streaming with stop/cancel support
- **PDF Upload & RAG** — Drag-and-drop or attach PDFs; auto-chunked, embedded, and indexed into FAISS + BM25
- **Voice Input** — Microphone button using Web Speech API for hands-free querying
- **Chat History** — Persistent sidebar with session management (create, load, delete), grouped by date
- **Document Library** — Navbar dropdown showing all indexed documents with delete capability
- **Source Citations** — Inline source chips on bot messages + collapsible right-side source panel
- **Agentic Routing** — Automatic query routing: document QA, web search, summarization, calculation, clarification
- **Dark/Light Theme** — System-aware with manual toggle, persisted in localStorage
- **Conversation Memory** — Multi-turn context with query rewriting for follow-up questions

---

## Quick Start

### Option 1: Batch Scripts (Windows)

```bash
# Start both backend + frontend
start.bat

# Stop all services
stop.bat
```

### Option 2: Manual

#### Backend

```bash
python -m venv venv
venv\Scripts\activate          # Windows

pip install -r requirements.txt

# Configure .env (see below)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# LLM Providers
GROK_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
GEMINI_API_KEY=your_gemini_api_key        # Optional

# Defaults
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.1-8b-instant

# Embeddings
EMBEDDING_PROVIDER=openrouter
EMBEDDING_MODEL_VERSION=text-embedding-3-small

# Auth
API_KEY=woxbot-dev-key
```

---

## Project Structure

```
WoxBot/
├── main.py                      # FastAPI entry-point
├── start.bat / stop.bat         # Windows service scripts
├── requirements.txt
├── .env                         # Environment config
├── app/
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   └── logger.py            # Structured logging
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py          # POST /api/chat (SSE streaming)
│   │   │   ├── ingest.py        # POST /api/ingest (PDF upload)
│   │   │   ├── sources.py       # GET/DELETE /api/sources
│   │   │   └── health.py        # GET /api/health
│   │   └── schemas.py           # Pydantic request/response models
│   ├── agent/                   # LangGraph agent + routing + memory
│   ├── ingestion/               # PDF parsing + smart chunking
│   ├── retrieval/               # FAISS + BM25 hybrid + reranker
│   ├── generation/              # Multi-LLM adapter + prompt templates
│   └── evaluation/              # RAGAS metrics
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx       # Main chat area + welcome screen
│   │   │   ├── InputBar.jsx         # Input with attach, voice, send/stop
│   │   │   ├── Navbar.jsx           # Header with model selector, library, theme
│   │   │   ├── Sidebar.jsx          # Persistent chat history sidebar
│   │   │   ├── ModelSelector.jsx    # Groq + OpenRouter model dropdown
│   │   │   ├── DocumentLibrary.jsx  # Navbar document list dropdown
│   │   │   ├── MessageBubble.jsx    # User/bot messages with markdown
│   │   │   └── SourcePanel.jsx      # Right-side source citations
│   │   ├── hooks/
│   │   │   ├── useStream.js     # POST-based SSE streaming
│   │   │   ├── useChat.js       # Message + session management
│   │   │   ├── useUpload.js     # PDF upload with progress
│   │   │   └── useVoice.js      # Web Speech API voice input
│   │   └── services/api.js      # Axios client
│   └── index.html
├── mcp_server/                  # FastMCP server
├── data/raw/                    # Source PDFs
├── vector_db/                   # FAISS index + BM25 + metadata
├── tests/
└── logs/
```

---

## API Endpoints

| Method | Endpoint              | Auth     | Description                |
| ------ | --------------------- | -------- | -------------------------- |
| GET    | `/api/health`         | None     | Health check               |
| POST   | `/api/chat`           | Required | SSE streaming chat         |
| POST   | `/api/ingest`         | Required | Upload PDF → chunk → index |
| GET    | `/api/sources`        | Required | List indexed documents     |
| DELETE | `/api/sources/{name}` | Required | Remove document + vectors  |

---

## Supported Models

### Groq (Fast Inference)

| Model               | ID                        |
| ------------------- | ------------------------- |
| Llama 3.1 8B        | `llama-3.1-8b-instant`    |
| Llama 3.3 70B       | `llama-3.3-70b-versatile` |
| Mixtral 8x7B        | `mixtral-8x7b-32768`      |
| Gemma 2 9B          | `gemma2-9b-it`            |

### OpenRouter (Free Tier)

| Model                | ID                                         |
| -------------------- | ------------------------------------------ |
| Gemini 2.0 Flash     | `google/gemini-2.0-flash-exp:free`         |
| DeepSeek V3          | `deepseek/deepseek-chat-v3-0324:free`      |
| Llama 3.3 70B        | `meta-llama/llama-3.3-70b-instruct:free`   |
| Qwen3 235B           | `qwen/qwen3-235b-a22b:free`               |
