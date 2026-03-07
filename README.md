# WoxBot 🤖

**Agentic RAG Academic Assistant for Woxsen University**

Stack: React + FastAPI + LangGraph + Gemini + FAISS + MCP

## Quick Start

### Backend
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Set your Gemini API key in .env
# GEMINI_API_KEY=your_key_here

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # Opens on http://localhost:5173
```

## Project Structure

```
WoxBot/
├── main.py                      # FastAPI entry-point
├── requirements.txt
├── .env                         # Environment config (not committed)
├── app/
│   ├── core/
│   │   ├── config.py            # Pydantic settings (all env vars)
│   │   └── logger.py            # Structured logging (file + console)
│   ├── api/routes/
│   │   └── health.py            # GET /api/health
│   ├── agent/                   # LangGraph agent (Phase 4)
│   ├── ingestion/               # PDF parsing + chunking (Phase 2)
│   ├── retrieval/               # FAISS + BM25 + reranker (Phase 3)
│   ├── generation/              # LLM adapter + prompts (Phase 4)
│   ├── evaluation/              # RAGAS metrics (Phase 7)
│   └── utils/                   # Shared helpers
├── frontend/                    # React 19 + Vite + TailwindCSS
│   ├── src/
│   │   ├── components/          # UI components (Phase 6)
│   │   ├── hooks/               # useStream, useChat, useUpload (Phase 6)
│   │   ├── services/            # Axios API calls (Phase 6)
│   │   └── styles/globals.css   # TailwindCSS base
│   └── .env                     # VITE_API_URL
├── mcp_server/                  # FastMCP server (Phase 7)
├── data/
│   ├── raw/                     # Source PDFs
│   └── processed/               # Chunked JSON cache
├── vector_db/                   # FAISS index + BM25 pkl + metadata
├── tests/
└── logs/                        # Auto-created at runtime
```

## API Endpoints

| Method | Endpoint              | Auth     | Description           |
|--------|-----------------------|----------|-----------------------|
| GET    | `/api/health`         | None     | `{status: "ok", version: "1.0"}` |
| POST   | `/api/ingest`         | Required | Upload PDF → index    |
| POST   | `/api/chat`           | Required | SSE streaming chat    |
| GET    | `/api/sources`        | Required | List indexed docs     |
| DELETE | `/api/sources/{id}`   | Required | Remove doc + vectors  |

## Multi-LLM Providers

| Provider     | Model                    | Free?            |
|-------------|--------------------------|------------------|
| Gemini       | gemini-1.5-flash         | Yes (15 req/min) |
| Grok         | grok-3                   | Trial credits    |
| OpenRouter   | google/gemini-flash-1.5  | Free tier        |
| PHI-3 Local  | phi3 (Ollama)            | Offline          |
