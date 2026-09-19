# Technical Requirements Document (TRD)

**Product:** arXiv Paper Curator  
**Repository:** [vb23abo/Research_Agent-using_RAG](https://github.com/vb23abo/Research_Agent-using_RAG)  
**Author:** Vijayalaxmi Bhambure ([@vb23abo](https://github.com/vb23abo))  
**Version:** 1.0  
**Status:** Active  
**Last updated:** 2026-09-19  
**License:** No license — all rights reserved  
**Companion:** [PRD](PRD.md)

---

## 1. Purpose

This document specifies the technical architecture, components, interfaces, data model, and non-functional requirements for arXiv Paper Curator. It is the engineering counterpart to the PRD and reflects the current implemented system.

---

## 2. System context

```
┌──────────────────────────────────────────────────────────────────┐
│                         Host / Docker network                    │
│                                                                  │
│  ┌────────┐  ┌──────────┐  ┌────────────┐  ┌─────────────────┐  │
│  │ FastAPI│  │  Gradio  │  │  Airflow   │  │ Telegram (opt.) │  │
│  │  :8000 │  │  :7861   │  │   :8080    │  │  (in API proc)  │  │
│  └───┬────┘  └────┬─────┘  └─────┬──────┘  └────────┬────────┘  │
│      │            │              │                   │           │
│      └────────────┴──────┬───────┴───────────────────┘           │
│                          │                                       │
│      ┌───────────────────┼───────────────────┐                   │
│      ▼                   ▼                   ▼                   │
│  ┌────────┐        ┌──────────┐        ┌──────────┐             │
│  │Postgres│        │OpenSearch│        │  Redis   │             │
│  │  :5432 │        │  :9200   │        │  :6379   │             │
│  └────────┘        └──────────┘        └──────────┘             │
│                          │                                       │
│                    ┌─────┴─────┐                                 │
│                    │  Ollama   │                                 │
│                    │  :11434   │                                 │
│                    └───────────┘                                 │
│                                                                  │
│  Observability: Langfuse web (:3001) + worker + ClickHouse +     │
│                 MinIO + Langfuse Postgres/Redis                  │
└──────────────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
   arXiv API (public)            Jina Embeddings API
```

### External systems

| System | Direction | Purpose |
|--------|-----------|---------|
| arXiv Atom API | Outbound | Paper metadata + PDF download |
| Jina AI Embeddings | Outbound | Query and document vectors (1024-d) |
| Telegram Bot API | Bidirectional | Optional chat interface |
| Ollama | Internal network | Local LLM inference |

---

## 3. Architecture overview

### 3.1 Style

- **Modular monolith API** — FastAPI process owns HTTP, DI, and optional Telegram polling
- **Async I/O** where clients support it (httpx, telegram, agent nodes)
- **Factory-based DI** — `make_*` factories + FastAPI `Depends` / app state
- **Pipeline orchestration** — Airflow for batch ingestion; LangGraph for agentic Q&A
- **Polyglot persistence** — Postgres (system of record for papers), OpenSearch (retrieval), Redis (cache)

### 3.2 Layering (`src/`)

| Layer | Responsibility | Examples |
|-------|----------------|----------|
| Routers | HTTP contracts | `ask.py`, `hybrid_search.py`, `agentic_ask.py` |
| Services | Business logic / clients | `opensearch/`, `ollama/`, `agents/`, `arxiv/` |
| Repositories | DB access | `repositories/paper.py` |
| Models | SQLAlchemy ORM | `models/paper.py` |
| Schemas | Pydantic I/O | `schemas/api/`, `schemas/arxiv/` |
| Config | Env-backed settings | `config.py` |

### 3.3 Runtime lifecycle

On API startup (`main.py` lifespan):

1. Load settings  
2. Connect Postgres  
3. Connect OpenSearch; ensure hybrid index exists  
4. Init arXiv, PDF parser, embeddings, Ollama, Langfuse, Redis  
5. Optionally start Telegram bot  
6. On shutdown: stop Telegram, teardown DB  

---

## 4. Component specifications

### 4.1 FastAPI application

| Item | Spec |
|------|------|
| Entry | `src/main.py` |
| Port | `8000` |
| Version | From `APP_VERSION` / settings |
| Docs | `/docs`, `/redoc` |
| Prefix | `/api/v1` for versioned routes |

### 4.2 Ingestion (Airflow)

**DAG:** `arxiv_paper_ingestion`  
**Schedule:** `0 6 * * 1-5` (Mon–Fri 06:00 UTC)  
**Max active runs:** 1  

| Task | Function | Responsibility |
|------|----------|----------------|
| `setup_environment` | `setup_environment` | Env / connectivity prep |
| `fetch_daily_papers` | `fetch_daily_papers` | arXiv fetch + PDF parse + Postgres write |
| `index_papers_hybrid` | `index_papers_hybrid` | Chunk, embed, OpenSearch index |
| `generate_daily_report` | `generate_daily_report` | Run summary |
| `cleanup_temp_files` | Bash | Delete PDFs older than 30 days under `/tmp` |

**Core library path:** `src/services/metadata_fetcher.py` orchestrates fetch/parse/store; indexing via `src/services/indexing/`.

### 4.3 PDF parsing

| Item | Spec |
|------|------|
| Engine | Docling |
| Limits | `PDF_PARSER__MAX_PAGES` (default 30), `MAX_FILE_SIZE_MB` (20) |
| OCR | Off by default |
| Tables | Structure extraction on by default |
| Output | Raw text, sections JSON, references when available |

### 4.4 Chunking

| Setting | Default | Notes |
|---------|---------|-------|
| `CHUNKING__CHUNK_SIZE` | 600 words | Target chunk size |
| `CHUNKING__OVERLAP_SIZE` | 100 words | Overlap between chunks |
| `CHUNKING__MIN_CHUNK_SIZE` | 100 words | Drop tiny fragments |
| `CHUNKING__SECTION_BASED` | `true` | Prefer section boundaries |

Implementation: `src/services/indexing/text_chunker.py`.

### 4.5 OpenSearch

| Item | Spec |
|------|------|
| Version | 2.19 |
| Index | `{OPENSEARCH__INDEX_NAME}-{CHUNK_INDEX_SUFFIX}` (e.g. `arxiv-papers-chunks`) |
| Lexical | BM25 over chunk text + metadata fields |
| Vector | kNN, dim `1024`, space `cosinesimil` |
| Hybrid | RRF pipeline (`OPENSEARCH__RRF_PIPELINE_NAME`) |
| Client | `src/services/opensearch/client.py` |
| Query build | `query_builder.py` |
| Index config | `index_config_hybrid.py` |

**Search modes**

1. BM25 only  
2. Vector only (via embeddings)  
3. Hybrid (BM25 + vector fused)

If embedding generation fails, API callers fall back to BM25.

### 4.6 Embeddings

| Item | Spec |
|------|------|
| Provider | Jina AI |
| Client | `src/services/embeddings/jina_client.py` |
| Auth | `JINA_API_KEY` |
| Dimension | 1024 (must match OpenSearch mapping) |
| Uses | Document indexing + query-time hybrid search |

### 4.7 LLM (Ollama)

| Item | Spec |
|------|------|
| Host | `OLLAMA_HOST` (default `http://localhost:11434`) |
| Default model | `llama3.2:1b` (overridable per request) |
| Timeout | `OLLAMA_TIMEOUT` (default 300s) |
| Prompts | `src/services/ollama/prompts/` |
| Client | `src/services/ollama/client.py` |

### 4.8 Classic RAG

**Flow:** embed (optional) → `search_unified` → build context → Ollama generate → sources from hit `arxiv_id`s.

| Endpoint | Behavior |
|----------|----------|
| `POST /api/v1/ask` | Synchronous JSON response |
| `POST /api/v1/stream` | SSE token/chunk stream |

Tracing: Langfuse spans for embedding, search, generation.  
Caching: Redis keyed by normalized request parameters; TTL hours from `REDIS__` settings (default 6h).

### 4.9 Agentic RAG (LangGraph)

**Service:** `src/services/agents/agentic_rag.py`  
**Endpoint:** `POST /api/v1/ask-agentic`

**Graph nodes**

| Node | Role |
|------|------|
| `guardrail` | Score / decide in-domain vs out-of-scope |
| `out_of_scope` | Safe refusal path |
| `retrieve` | Emit tool call for retrieval |
| `tool_retrieve` | LangGraph `ToolNode` → OpenSearch retriever tool |
| `grade_documents` | Relevance grade → route generate vs rewrite |
| `rewrite_query` | Reformulate query; loop to retrieve |
| `generate_answer` | Final grounded generation |

**Config (`GraphConfig`):** model, top-k, hybrid flag, max retrieval attempts, guardrail threshold.

**Response extras:** `reasoning_steps`, `retrieval_attempts`, optional `trace_id`.

### 4.10 Cache (Redis)

| Item | Spec |
|------|------|
| Image | Redis 7 Alpine |
| Policy | `allkeys-lru`, 256MB max in Compose |
| Persistence | AOF enabled |
| Client | `src/services/cache/client.py` |
| Behavior | Exact-match cache; degrade gracefully if Redis down |

### 4.11 Observability (Langfuse)

Self-hosted Langfuse v3 stack in Compose (web, worker, Postgres, Redis, ClickHouse, MinIO).

| Item | Spec |
|------|------|
| Integration | `src/services/langfuse/` |
| Use | Trace RAG and agentic pipelines; optional feedback by `trace_id` |
| Toggle | Enable/disable via env |

### 4.12 Telegram bot

| Item | Spec |
|------|------|
| Library | `python-telegram-bot` 21.x |
| Mode | Polling (dev); webhook supported via config |
| Enable | `TELEGRAM__ENABLED=true` + `TELEGRAM__BOT_TOKEN` |
| Lifecycle | Started/stopped in FastAPI lifespan |
| Features | Commands (`/start`, `/help`, `/ask`, `/search`, `/settings`, `/status`, …), free-text RAG, Markdown formatting |

### 4.13 Gradio UI

| Item | Spec |
|------|------|
| Module | `src/gradio_app.py` |
| Launcher | `gradio_launcher.py` |
| Port | `7861` |
| Role | Interactive chat over classic/streaming RAG |

---

## 5. API contracts

Base URL: `http://localhost:8000`

### 5.1 Health

```
GET /api/v1/health
```

Returns service liveness / dependency status used by Compose healthchecks.

### 5.2 Hybrid search

```
POST /api/v1/hybrid-search/
```

**Request (conceptual):** `query`, `size`, `from_`, `categories`, `use_hybrid`, `min_score`, `latest_papers`  
**Response:** list of hits (`arxiv_id`, title, authors, abstract, score, chunk fields, highlights, …)

### 5.3 Classic ask

```
POST /api/v1/ask
Content-Type: application/json

{
  "query": "What are transformers in machine learning?",
  "top_k": 3,
  "use_hybrid": true,
  "model": "llama3.2:1b",
  "categories": ["cs.AI", "cs.LG"]
}
```

**Response:** `query`, `answer`, `sources[]`, `chunks_used`, `search_mode`

### 5.4 Streaming ask

```
POST /api/v1/stream
```

Same request body as ask; response is `text/event-stream`.

### 5.5 Agentic ask

```
POST /api/v1/ask-agentic
```

Same core request fields as ask.  
**Response adds:** `reasoning_steps[]`, `retrieval_attempts`, optional `trace_id`.

### 5.6 Feedback (optional)

```
POST /api/v1/...  # feedback payload with trace_id, score, comment
```

Records user feedback against a Langfuse trace when configured.

OpenAPI is the source of truth at runtime: `/docs`.

---

## 6. Data model

### 6.1 PostgreSQL — `papers`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | Internal id |
| `arxiv_id` | String unique indexed | External id |
| `title` | String | |
| `authors` | JSON | |
| `abstract` | Text | |
| `categories` | JSON | |
| `published_date` | DateTime | |
| `pdf_url` | String | |
| `raw_text` | Text nullable | Parsed body |
| `sections` | JSON nullable | Structured sections |
| `references` | JSON nullable | |
| `parser_used` | String nullable | |
| `parser_metadata` | JSON nullable | |
| `pdf_processed` | Boolean | |
| `pdf_processing_date` | DateTime nullable | |
| `created_at` / `updated_at` | DateTime | |

ORM: `src/models/paper.py`  
Access: `PaperRepository`

### 6.2 OpenSearch — hybrid chunk documents

Logical fields (representative):

- Identifiers: `arxiv_id`, `chunk_id`
- Content: `chunk_text`, `section_name`, `title`, `abstract`
- Metadata: `authors`, `categories`, `published_date`, `pdf_url`
- Vector: embedding field dim 1024
- Scoring: BM25 + kNN + RRF pipeline

### 6.3 Redis

- Cache entries for RAG responses (serialized payload + TTL)
- No durable source of truth; safe to flush

### 6.4 Langfuse stores

Managed by Langfuse containers (Postgres, ClickHouse, object storage). Application does not own these schemas directly.

---

## 7. Configuration

Settings are loaded via Pydantic Settings (`src/config.py`) from `.env`, with nested delimiter `__`.

| Prefix / key | Area |
|--------------|------|
| `POSTGRES_DATABASE_URL` | Primary DB |
| `ARXIV__*` | Fetch rate limits, category, cache dir |
| `PDF_PARSER__*` | Docling limits |
| `CHUNKING__*` | Chunk sizes |
| `OPENSEARCH__*` | Host, index, vector, RRF |
| `JINA_API_KEY` | Embeddings |
| `OLLAMA_*` | Host, model, timeout |
| `REDIS__*` | Cache host + TTL |
| `LANGFUSE_*` / `LANGFUSE__*` | Tracing |
| `TELEGRAM__*` | Bot enablement and token |
| `ENVIRONMENT` | `development` \| `staging` \| `production` |

Compose overrides hostnames to service DNS names (`postgres`, `opensearch`, `redis`, `ollama`, …).

---

## 8. Non-functional requirements

### 8.1 Performance

| Scenario | Expectation |
|----------|-------------|
| Health check | &lt; 1s under normal load |
| Hybrid search only | Typically low single-digit seconds |
| First RAG (small local model) | Often 15–60s depending on hardware/model |
| Cached identical RAG | Sub-second when Redis hit |
| Concurrent users | Single-node; suitable for personal/small-team use |

### 8.2 Reliability

- Docker `restart: unless-stopped` on critical infra services  
- API depends on healthy Postgres, OpenSearch, Redis before start  
- Embedding failure → BM25 fallback  
- Cache / Langfuse failure → continue without blocking core path where implemented  

### 8.3 Security

| Control | Status |
|---------|--------|
| Secrets in env / `.env` (not committed) | Required |
| OpenSearch security plugin | Disabled in local Compose (dev) |
| API authentication | Not in v1 (open local network) |
| Telegram allowlist | Optional via settings |
| TLS termination | Operator responsibility for public deploy |

**Production hardening (required before public exposure):** enable auth, TLS, restrict ports, rotate Langfuse/MinIO secrets, enable OpenSearch security or private network only.

### 8.4 Scalability

v1 is **vertical / single-host**. Horizontal scaling of API is possible behind a load balancer if Telegram uses webhook mode and shared Redis/Postgres/OpenSearch; not validated as a multi-replica product yet.

### 8.5 Observability

- Application logs (stdout)  
- Langfuse traces for RAG spans  
- Docker healthchecks on API, OpenSearch, Postgres, Redis, Ollama, Airflow, Langfuse  

### 8.6 Maintainability

- Python 3.12  
- UV lockfile (`uv.lock`)  
- Ruff formatting/lint; mypy available  
- Pytest unit, API, and integration tests  
- Pre-commit config present  

### 8.7 Resource requirements

| Resource | Minimum recommended |
|----------|---------------------|
| RAM | 8GB+ for Docker |
| Disk | 20GB+ free (images, indexes, PDFs, models) |
| CPU | 4+ cores preferred for local LLM |

---

## 9. Deployment

### 9.1 Local / default

```bash
cp .env.example .env
uv sync
docker compose up --build -d
```

Optional Gradio (host):

```bash
uv run python gradio_launcher.py
```

### 9.2 Compose services (summary)

| Service | Container | Ports |
|---------|-----------|-------|
| `api` | `rag-api` | 8000 |
| `postgres` | `rag-postgres` | 5432 |
| `opensearch` | `rag-opensearch` | 9200, 9600 |
| `opensearch-dashboards` | `rag-dashboards` | 5601 |
| `airflow` | `rag-airflow` | 8080 |
| `ollama` | `rag-ollama` | 11434 |
| `redis` | `rag-redis` | 6379 |
| `langfuse-web` | `rag-langfuse-web` | 3001→3000 |
| Langfuse deps | worker, postgres, redis, clickhouse, minio | various |

Network: `rag-network` (bridge).

### 9.3 Build

API image built from repo `Dockerfile`. Airflow image built from `airflow/Dockerfile` with `src/` mounted for shared libraries.

---

## 10. Testing strategy

| Layer | Location | Focus |
|-------|----------|-------|
| Unit | `tests/unit/` | Config, clients, agents, parsers, query builder |
| API | `tests/api/` | Routers with app fixtures |
| Integration | `tests/integration/` | Service wiring / containers where applicable |

Commands:

```bash
uv run pytest
uv run pytest --cov=src --cov-report=html
# or: make test / make test-cov
```

Env for tests: `.env.test` (see `pyproject.toml` pytest config).

---

## 11. Error handling and resilience

| Failure | Expected behavior |
|---------|-------------------|
| OpenSearch down | Search/ask return 503 or degraded messaging |
| Jina error | Log warning; BM25-only search |
| Ollama timeout | Request error surfaced to client |
| Redis down | Skip cache; full pipeline |
| Langfuse down | Log; do not fail user Q&A |
| Out-of-scope agentic query | Guardrail → out-of-scope response |
| Empty agentic query | `ValueError` → HTTP error |

Custom exceptions: `src/exceptions.py` (`MetadataFetchingException`, `PipelineException`, …).

---

## 12. Technology decisions (ADRs lite)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Search engine | OpenSearch | BM25 + kNN + pipelines in one system |
| Hybrid fusion | RRF | Robust rank fusion without fragile score calibration |
| Embeddings | Jina API | Strong quality; dim fixed at 1024 |
| LLM | Ollama local | Privacy, zero inference API cost |
| Agents | LangGraph | Explicit stateful control flow |
| Batch jobs | Airflow | Standard for scheduled ingestion |
| PDF parsing | Docling | Scientific layout / structure |
| API | FastAPI | Async, OpenAPI, typing |
| Cache | Redis exact match | Simple, high ROI for demos and repeated asks |

---

## 13. Constraints and known limitations

1. Default LLM (`llama3.2:1b`) prioritizes resource use over answer quality.  
2. OpenSearch runs with security plugin disabled in Compose.  
3. No first-class API auth in v1.  
4. Telegram sessions are in-memory (not multi-replica safe).  
5. Hybrid search requires external Jina key.  
6. Corpus limited by configured category, `max_results`, and PDF parse limits.  
7. Langfuse Compose defaults include development secrets — must be rotated for any shared environment.

---

## 14. Compliance with PRD

| PRD goal | Technical coverage |
|----------|-------------------|
| G1 Ingestion | Airflow DAG + MetadataFetcher + Postgres |
| G2 Hybrid retrieval | OpenSearch hybrid index + Jina + RRF |
| G3 Cited Q&A | `/ask`, `/stream` + source URL construction |
| G4 Agentic behavior | LangGraph nodes in `services/agents/` |
| G5 Interfaces | FastAPI, Gradio, Telegram |
| G6 Ops basics | Redis, Langfuse, healthchecks, tests, Compose |

---

## 15. Document control

| Change | Update this TRD when… |
|--------|------------------------|
| New endpoint or breaking schema | API section |
| New datastore or index mapping | Data model |
| New service dependency | Context + Compose |
| Changed NFR targets | Section 8 |

**Related**

- [PRD](PRD.md)  
- [README](../README.md)  
- [LICENSE](../LICENSE) — no open-source license; all rights reserved  
- OpenAPI: `http://localhost:8000/docs`  
