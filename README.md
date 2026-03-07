# WoxBot 🤖

**Agentic RAG system for Woxsen University**

## Quick Start

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
WoxBot/
├── main.py                  # FastAPI entry-point
├── requirements.txt
├── .env                     # Environment config (not committed)
├── app/
│   ├── core/
│   │   ├── config.py        # Pydantic settings
│   │   └── logger.py        # Structured logging
│   ├── api/
│   │   └── routes/
│   │       └── health.py    # /api/health endpoint
│   ├── agents/              # (Phase 2+)
│   ├── rag/                 # (Phase 2+)
│   ├── services/            # (Phase 2+)
│   └── models/              # (Phase 2+)
├── data/
│   ├── raw/                 # Source documents
│   └── vectorstore/         # Persisted embeddings
├── tests/
└── logs/                    # Auto-created at runtime
```

## API

| Method | Endpoint       | Description         |
|--------|---------------|---------------------|
| GET    | `/api/health` | Liveness check      |
