# arXiv Paper Curator

Fetches arXiv papers, parses the PDFs, stores them, and answers a question from the stored text with links to the source PDFs.

**Demo:** [Local chat recording](recordings/arxiv-rag-demo.mov) — one question answered from three indexed papers (WeightBench, game-rule agents, and EEG/ECG), using hybrid search and three PDF sources.

---

## Features

- **Ingestion.** An Airflow DAG fetches a paper, parses the PDF, stores it, and indexes the chunks. The DAG has been run from the scheduler.
- **Search.** Keyword and vector search over the stored text.
- **Answer.** A local model answers from the matching passages and includes links to the source PDFs. The same answer is available from FastAPI, Gradio, and Telegram.
- **Agent path.** The agent checks the question, grades the passages, and rewrites the query when they do not fit.
- **Trace.** Langfuse records the embedding, the search, and the answer. The reply is still returned if tracing is off.

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
| Orchestration | Apache Airflow 2.10.3 |
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
- Optional: a Telegram bot token, and Langfuse keys if you want traces shown

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/vb23abo/Research_Agent-using_RAG.git
cd Research_Agent-using_RAG

# 2. Configure
cp .env.example .env
# Set JINA_API_KEY (required for hybrid search)
# Telegram starts only when TELEGRAM__ENABLED=true and TELEGRAM__BOT_TOKEN is a real token
# Tracing starts when LANGFUSE__PUBLIC_KEY and LANGFUSE__SECRET_KEY are set
# Inside Compose, LANGFUSE__HOST is http://langfuse-web:3000

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
| Langfuse | http://localhost:3001 | Pipeline tracing. Sign in `admin@example.com` / `admin123`. Project name: Agentic RAG |
| Airflow | http://localhost:8080 | Ingestion DAGs |
| OpenSearch Dashboards | http://localhost:5601 | Index inspection |
| OpenSearch | http://localhost:9200 | Search API |
| Ollama | http://localhost:11434 | Local LLM |

Airflow UI login is `admin` / `admin`, created by `airflow/entrypoint.sh` on first start.

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Service health |
| `GET` | `/api/v1/papers/` | Stored papers |
| `GET` | `/api/v1/papers/{arxiv_id}` | One stored paper |
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
| `LANGFUSE__PUBLIC_KEY`, `LANGFUSE__SECRET_KEY` | No | Tracing. The API ignores the single-underscore names |

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
REDIS__HOST=127.0.0.1 uv run pytest
uv run python gradio_launcher.py
```

On the host, Redis is `127.0.0.1`. The Compose `.env` uses the hostname `redis`, which only resolves inside Docker. Set `REDIS__HOST` for pytest so the API tests can reach the running Redis.

---

## Ingestion pipeline

The `arxiv_paper_ingestion` Airflow DAG (weekdays 06:00 UTC by default):

1. Set up environment  
2. Fetch papers from arXiv (rate-limited)  
3. Parse PDFs and store metadata in PostgreSQL  
4. Chunk, embed, and index into OpenSearch (hybrid)  
5. Generate a daily report and clean temp PDFs  

Trigger manually from the Airflow UI if you need an immediate backfill. PDFs longer than 30 pages are stored from the abstract and are not parsed. Docling can hold the CPU for several minutes, so `AIRFLOW__SCHEDULER__SCHEDULER_ZOMBIE_TASK_THRESHOLD` is 7200 seconds. The Airflow image pins CPU `torch==2.8.0` so the install does not pull CUDA libraries.

The fetch and index task functions were run once on 26 November 2026 for a single `cs.AI` paper (`2611.34942`) without starting the Airflow scheduler. That run stored the paper and indexed 12 chunks. A later `/ask` cited `https://arxiv.org/pdf/2611.34942.pdf`.

On 27 November 2026 the scheduler was running and `arxiv_paper_ingestion` was unpaused. The weekday run for the 24 November papers fetched 15 papers, parsed 12 PDFs, and indexed 180 chunks. Three PDFs returned no Docling result (`2611.33493`, `2611.33470`, `2611.33417`). The following weekday slot was marked failed while Docling was still parsing, because the scheduler's old 300 second zombie limit had not yet been raised.

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Services not ready | Wait 2–3 min; `docker compose logs -f` |
| Port conflicts | Free 8000, 8080, 5432, 9200, 11434, 3001, 7861 |
| Hybrid search fails | Confirm `JINA_API_KEY` in `.env` |
| Telegram silent | `TELEGRAM__ENABLED=true` and a real bot token. Compose runs the API with one worker so the bot has one polling connection. Check `docker compose logs api` |
| OOM / slow Docker | Increase Docker Desktop memory (8GB+) |
| Hard reset | `docker compose down -v && docker compose up --build -d` |

---

## What was checked locally

Checked on 26 November 2026 against the core stack (API, Postgres, OpenSearch, Redis, Ollama `llama3.2:1b`). The Airflow scheduler, Telegram, and Langfuse were not started.

| Check | Result |
|-------|--------|
| Unit tests (`tests/unit`) | 91 passed |
| API tests (`tests/api`) | 26 passed |
| Integration tests (`tests/integration`) | 3 passed: one live arXiv query, OpenSearch health, settings load |
| Classic RAG | The [demo recording](recordings/arxiv-rag-demo.mov) shows one question answered from three papers, with three PDF sources |
| Agentic RAG | A weight-space programming question scored 75/100, retrieved a paper, and cited `https://arxiv.org/pdf/2611.18553v1.pdf`. A chocolate-cake question scored 40/100 and was refused |
| Ingestion tasks | One new paper fetched, parsed, stored, and indexed, then cited by `/ask` |

Checked again on 27 November 2026 with the same core stack, plus the Airflow scheduler, Telegram, and Langfuse.

| Check | Result |
|-------|--------|
| Airflow | Scheduler healthy. The weekday DAG was unpaused. The 24 November slot stored 15 papers and indexed 180 chunks |
| Telegram | Bot `@arXiv_research_assistant_bot` started and accepted the token |
| Langfuse | UI healthy at http://localhost:3001. One `/ask` about spectrum adaptation was stored as trace `rag_request`, with embedding, search, prompt, and generation steps, and cited `https://arxiv.org/pdf/2611.34942.pdf` |
| Gradio | http://localhost:7861 returned the chat page |

## Author

**Vijayalaxmi Bhambure** ([@vb23abo](https://github.com/vb23abo))

Repository: [vb23abo/Research_Agent-using_RAG](https://github.com/vb23abo/Research_Agent-using_RAG)

---

## License

MIT. See [LICENSE](LICENSE).
