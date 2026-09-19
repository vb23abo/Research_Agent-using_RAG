# arXiv Paper Curator

**Agentic RAG research assistant for arXiv AI papers.**

Ingests academic papers from arXiv, indexes them with hybrid search (BM25 + vectors), and answers research questions with cited sources — via REST API, Gradio UI, or Telegram.

---

## Features

- **Automated ingestion** — Daily Airflow pipeline fetches CS.AI papers, parses PDFs, and stores metadata
- **Hybrid search** — Keyword (BM25) + semantic (Jina embeddings) retrieval with RRF fusion
- **Classic RAG** — Retrieve relevant chunks and generate grounded answers with a local LLM (Ollama)
- **Agentic RAG** — LangGraph workflow with guardrails, document grading, and query rewriting
- **Streaming answers** — Server-Sent Events for real-time response delivery
- **Observability** — Langfuse tracing for embed → search → generate pipelines
- **Response caching** — Redis exact-match cache for repeated queries
- **Interfaces** — FastAPI docs, Gradio chat UI, optional Telegram bot

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  arXiv API  │────▶│   Airflow    │────▶│   PostgreSQL    │
└─────────────┘     │  (ingest)    │     │  (paper metadata)│
                    └──────┬───────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  OpenSearch  │◀── Jina embeddings
                    │ (hybrid idx) │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐     ┌──────────┐      ┌────────────┐
   │ FastAPI  │     │  Gradio  │      │  Telegram  │
   │  /ask    │     │   UI     │      │    Bot     │
   └────┬─────┘     └────┬─────┘      └─────┬──────┘
        │                │                  │
        └────────────────┼──────────────────┘
                         ▼
                  ┌──────────────┐
                  │    Ollama    │
                  │  (local LLM) │
                  └──────────────┘
```

**Agentic RAG flow:**

```
Query → Guardrail → Retrieve → Grade docs
                      ↑              │
                      └── Rewrite ←──┘ (if irrelevant)
                                       │
                                       ▼
                                 Generate answer + sources
```

For product scope and technical design, see:

| Document | Description |
|----------|-------------|
| [PRD](docs/PRD.md) | Product requirements, users, features, success metrics |
| [TRD](docs/TRD.md) | Architecture, APIs, data model, NFRs, deployment |

---

## Tech stack

| Component | Technology |
|-----------|------------|
| API | FastAPI, Pydantic Settings |
| Metadata store | PostgreSQL 16 |
| Search | OpenSearch 2.19 (BM25 + kNN) |
| Embeddings | Jina AI |
| LLM | Ollama (local) |
| Orchestration | Apache Airflow 3 |
| PDF parsing | Docling |
| Agents | LangGraph / LangChain |
| Cache | Redis 7 |
| Observability | Langfuse |
| UI | Gradio |
| Messaging | python-telegram-bot |
| Packaging | UV, Docker Compose |

---

## Prerequisites

- Docker Desktop (Compose)
- Python 3.12+
- [UV](https://docs.astral.sh/uv/getting-started/installation/)
- 8GB+ RAM, 20GB+ free disk
- Jina API key (for hybrid/semantic search)
- Optional: Telegram bot token, Langfuse keys (self-hosted defaults work locally)

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/vb23abo/Research_Agent-using_RAG.git
cd Research_Agent-using_RAG

# 2. Configure
cp .env.example .env
# Set JINA_API_KEY (required for hybrid search)
# Optionally set TELEGRAM__BOT_TOKEN and Langfuse keys

# 3. Install dependencies
uv sync

# 4. Start stack
docker compose up --build -d

# 5. Health check
curl http://localhost:8000/api/v1/health
```

First boot can take a few minutes while images pull and services become healthy.

---

## Services

| Service | URL | Purpose |
|---------|-----|---------|
| API & Swagger | http://localhost:8000/docs | Interactive API |
| Gradio UI | http://localhost:7861 | Chat interface (`uv run python gradio_launcher.py`) |
| Langfuse | http://localhost:3001 | Pipeline tracing |
| Airflow | http://localhost:8080 | Ingestion DAGs |
| OpenSearch Dashboards | http://localhost:5601 | Index inspection |
| OpenSearch | http://localhost:9200 | Search API |
| Ollama | http://localhost:11434 | Local LLM |

Airflow credentials are written to `airflow/simple_auth_manager_passwords.json.generated` on first start.

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Service health |
| `POST` | `/api/v1/hybrid-search/` | BM25 / hybrid chunk search |
| `POST` | `/api/v1/ask` | Classic RAG Q&A |
| `POST` | `/api/v1/stream` | Streaming RAG (SSE) |
| `POST` | `/api/v1/ask-agentic` | Agentic RAG with reasoning steps |

**Example — agentic ask:**

```bash
curl -X POST http://localhost:8000/api/v1/ask-agentic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are attention mechanisms in transformers?",
    "top_k": 3,
    "use_hybrid": true
  }'
```

Full request/response schemas: http://localhost:8000/docs

---

## Project structure

```
├── src/
│   ├── main.py                 # FastAPI entry + lifespan
│   ├── config.py               # Environment settings
│   ├── routers/                # HTTP endpoints
│   ├── services/
│   │   ├── arxiv/              # Paper fetching
│   │   ├── pdf_parser/         # Docling PDF parsing
│   │   ├── indexing/           # Chunking + hybrid indexing
│   │   ├── embeddings/         # Jina client
│   │   ├── opensearch/         # Search client
│   │   ├── ollama/             # LLM client + prompts
│   │   ├── agents/             # LangGraph agentic RAG
│   │   ├── cache/              # Redis
│   │   ├── langfuse/           # Tracing
│   │   └── telegram/           # Bot
│   ├── models/                 # SQLAlchemy models
│   ├── repositories/           # Data access
│   ├── schemas/                # Pydantic schemas
│   └── gradio_app.py           # Web UI
├── airflow/dags/               # Paper ingestion pipeline
├── docs/                       # PRD, TRD
├── tests/                      # Unit, API, integration tests
├── compose.yml                 # Docker services
└── pyproject.toml
```

---

## Configuration

Copy `.env.example` → `.env`. Important variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `JINA_API_KEY` | Yes (hybrid) | Embeddings for semantic search |
| `TELEGRAM__BOT_TOKEN` | No | Enable Telegram bot |
| `TELEGRAM__ENABLED` | No | Set `true` to start the bot |
| `OLLAMA_MODEL` | No | Default `llama3.2:1b` |
| `ARXIV__SEARCH_CATEGORY` | No | Default `cs.AI` |
| `LANGFUSE_*` | No | Tracing (self-hosted via Compose) |

See `.env.example` for the full list.

---

## Development

```bash
make help      # List commands
make start     # docker compose up --build -d
make health    # Check services
make test      # Run pytest
make format    # Ruff format
make lint      # Ruff + mypy
make stop      # Tear down containers
make clean     # Remove containers + volumes
```

Or without Make:

```bash
docker compose up --build -d
uv run pytest
uv run python gradio_launcher.py
```

---

## Ingestion pipeline

The `arxiv_paper_ingestion` Airflow DAG (weekdays 06:00 UTC by default):

1. Set up environment  
2. Fetch papers from arXiv (rate-limited)  
3. Parse PDFs and store metadata in PostgreSQL  
4. Chunk, embed, and index into OpenSearch (hybrid)  
5. Generate a daily report and clean temp PDFs  

Trigger manually from the Airflow UI if you need an immediate backfill.

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Services not ready | Wait 2–3 min; `docker compose logs -f` |
| Port conflicts | Free 8000, 8080, 5432, 9200, 11434, 3001, 7861 |
| Hybrid search fails | Confirm `JINA_API_KEY` in `.env` |
| Telegram silent | `TELEGRAM__ENABLED=true` + valid bot token; check `docker compose logs api` |
| OOM / slow Docker | Increase Docker Desktop memory (8GB+) |
| Hard reset | `docker compose down -v && docker compose up --build -d` |

---

## Author

**Vijayalaxmi Bhambure** ([@vb23abo](https://github.com/vb23abo))

Repository: [vb23abo/Research_Agent-using_RAG](https://github.com/vb23abo/Research_Agent-using_RAG)

---

## License

No license. All rights reserved. See [LICENSE](LICENSE).
