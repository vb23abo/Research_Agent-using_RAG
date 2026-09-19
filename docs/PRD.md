# Product Requirements Document (PRD)

**Product:** arXiv Paper Curator  
**Repository:** [vb23abo/Research_Agent-using_RAG](https://github.com/vb23abo/Research_Agent-using_RAG)  
**Author:** Vijayalaxmi Bhambure ([@vb23abo](https://github.com/vb23abo))  
**Version:** 1.0  
**Status:** Active  
**Last updated:** 2026-09-19  
**License:** No license — all rights reserved  

---

## 1. Overview

### 1.1 Summary

arXiv Paper Curator is a self-hosted research assistant that continuously ingests AI/ML papers from arXiv, indexes their content for hybrid retrieval, and answers natural-language research questions with grounded, cited responses.

Users interact through a REST API, a Gradio web chat, or an optional Telegram bot. Generation runs locally via Ollama for privacy and cost control; embeddings use Jina AI for semantic search quality.

### 1.2 Problem statement

Researchers and engineers spend significant time:

- Searching arXiv manually for relevant papers
- Opening and skimming PDFs to find specific claims or methods
- Re-running similar literature questions without reusable context
- Trusting LLM answers that are not grounded in primary sources

Existing chatbots either lack domain grounding in arXiv literature, or are cloud-only black boxes without ingestion control, observability, or local LLM options.

### 1.3 Solution

A production-oriented RAG system that:

1. Automatically fetches and parses papers in a chosen arXiv category (default: `cs.AI`)
2. Indexes chunks with keyword + vector search
3. Answers questions using retrieved context and cites source PDFs
4. Optionally uses an agentic workflow to validate relevance and refine queries
5. Exposes the same capabilities via API, web UI, and Telegram

### 1.4 Product principles

| Principle | Meaning |
|-----------|---------|
| Grounded answers | Prefer retrieval + citation over free-form hallucination |
| Search-first quality | Strong BM25 foundation before (and with) vectors |
| Local-first generation | LLM inference stays on the operator’s machine by default |
| Observable by default | Traces and cache metrics for debugging and latency |
| Multi-interface | Same core pipeline behind API, Gradio, and Telegram |
| Operator-owned data | Papers and indexes run in the operator’s Docker stack |

---

## 2. Goals and non-goals

### 2.1 Goals

| ID | Goal | Success signal |
|----|------|----------------|
| G1 | Automate daily paper ingestion for a configured arXiv category | DAG completes successfully on schedule; papers appear in Postgres + OpenSearch |
| G2 | Enable accurate hybrid retrieval over paper chunks | Relevant papers/chunks returned for research queries |
| G3 | Deliver cited Q&A over ingested literature | Answers include arXiv PDF source links |
| G4 | Support agentic retrieval (guardrails, grading, rewrite) | Off-topic queries refused; weak retrieval triggers rewrite |
| G5 | Provide usable interfaces for developers and end users | API docs + Gradio + optional Telegram work end-to-end |
| G6 | Provide production ops basics | Health checks, Redis cache, Langfuse traces, tests |

### 2.2 Non-goals (v1)

- Multi-tenant SaaS with billing, auth providers, or org RBAC
- Fine-tuning custom embedding or LLM models
- Full-text legal/medical compliance certification
- Real-time collaboration / shared notebooks
- Guaranteed coverage of all arXiv categories out of the box
- Replacing dedicated literature review tools (Zotero, Semantic Scholar UI, etc.)

---

## 3. Users and personas

### 3.1 Primary personas

**P1 — Independent ML / AI engineer**  
Wants a private assistant over recent AI papers; runs the stack locally; uses API or Gradio.

**P2 — Research student / academic**  
Asks conceptual and comparative questions (“How does X differ from Y?”); wants citations and PDF links; may prefer Telegram on mobile.

**P3 — Platform / backend engineer**  
Integrates `/ask` or `/ask-agentic` into internal tools; cares about schemas, health, caching, and traces.

### 3.2 Secondary persona

**P4 — Operator / maintainer**  
Owns Docker Compose, env config, Airflow DAGs, disk usage for PDFs, and model pulls in Ollama.

---

## 4. User journeys

### 4.1 First-time setup

1. Clone repo, copy `.env.example` → `.env`, set `JINA_API_KEY`
2. `uv sync` and `docker compose up --build -d`
3. Confirm `/api/v1/health`
4. Trigger or wait for ingestion DAG
5. Ask a question via Swagger or Gradio

### 4.2 Research Q&A (classic RAG)

1. User submits a research question
2. System embeds query (if hybrid), searches OpenSearch, builds prompt
3. Ollama generates an answer grounded in retrieved chunks
4. User receives answer + source PDF URLs
5. Repeat queries hit Redis cache when identical

### 4.3 Agentic research Q&A

1. User submits a question to `/ask-agentic` or Telegram
2. Guardrail checks domain fit
3. If in-scope: retrieve → grade → optionally rewrite → generate
4. Response includes answer, sources, reasoning steps, retrieval attempt count

### 4.4 Mobile via Telegram

1. Operator enables bot with token
2. User sends `/start`, then a natural-language question
3. Bot runs RAG pipeline, returns Markdown answer with arXiv links
4. User adjusts settings (top-k, hybrid vs BM25) via `/settings`

---

## 5. Functional requirements

### 5.1 Paper ingestion

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-I1 | Fetch papers from arXiv API for a configured category | Must |
| FR-I2 | Respect rate limits and retry failed downloads | Must |
| FR-I3 | Parse PDFs into text/sections (Docling) | Must |
| FR-I4 | Persist paper metadata and parsed content in PostgreSQL | Must |
| FR-I5 | Chunk documents (section-aware when possible) | Must |
| FR-I6 | Embed chunks and index into OpenSearch hybrid index | Must |
| FR-I7 | Run ingestion on a schedule via Airflow | Must |
| FR-I8 | Support manual DAG trigger for backfill/demo | Should |
| FR-I9 | Clean up old temporary PDF files | Should |

### 5.2 Search

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-S1 | BM25 keyword search over chunks | Must |
| FR-S2 | Vector (kNN) search using query embeddings | Must |
| FR-S3 | Hybrid search combining BM25 + vector (RRF) | Must |
| FR-S4 | Filter by arXiv categories | Should |
| FR-S5 | Graceful fallback to BM25 if embeddings fail | Must |
| FR-S6 | Expose search via REST API | Must |

### 5.3 Question answering (RAG)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-Q1 | Classic RAG: retrieve top-k → generate answer | Must |
| FR-Q2 | Include source PDF URLs in responses | Must |
| FR-Q3 | Support streaming responses (SSE) | Must |
| FR-Q4 | Configurable `top_k`, hybrid flag, model, categories | Must |
| FR-Q5 | Use local Ollama for generation by default | Must |

### 5.4 Agentic RAG

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-A1 | Guardrail: detect out-of-scope queries | Must |
| FR-A2 | Retrieve via tool-backed OpenSearch | Must |
| FR-A3 | Grade retrieved documents for relevance | Must |
| FR-A4 | Rewrite query and retry when docs are irrelevant | Must |
| FR-A5 | Cap retrieval attempts | Must |
| FR-A6 | Return reasoning steps and attempt count | Must |
| FR-A7 | Optional Langfuse trace id for feedback | Should |

### 5.5 Interfaces

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-U1 | FastAPI with OpenAPI docs | Must |
| FR-U2 | Gradio chat UI for interactive Q&A | Must |
| FR-U3 | Optional Telegram bot (commands + free text) | Should |
| FR-U4 | Health endpoint for liveness/readiness | Must |

### 5.6 Operations

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-O1 | Redis caching of RAG responses | Must |
| FR-O2 | Langfuse (or equivalent) end-to-end traces | Should |
| FR-O3 | Docker Compose one-command local deploy | Must |
| FR-O4 | Automated test suite (unit / API / integration) | Must |
| FR-O5 | Configurable via environment variables | Must |

---

## 6. Non-functional requirements (product view)

Detailed technical NFRs live in the [TRD](TRD.md). Product-level expectations:

| Area | Expectation |
|------|-------------|
| Latency | First uncached RAG answer typically tens of seconds (local small LLM); cached repeats near-instant |
| Privacy | Paper corpus and LLM generation remain local; only embedding calls leave the host (Jina) unless replaced |
| Reliability | Services restart via Docker; search falls back to BM25 without embeddings |
| Usability | OpenAPI + Gradio usable without reading source |
| Cost | Core stack free/self-hosted; Jina usage is the main external cost |

---

## 7. Scope by release

### 7.1 Current release (v1.0) — in scope

- arXiv ingestion + Postgres storage
- Hybrid OpenSearch indexing
- Classic RAG (`/ask`, `/stream`)
- Agentic RAG (`/ask-agentic`)
- Gradio UI
- Redis cache + Langfuse stack in Compose
- Optional Telegram bot
- Health checks, Makefile, tests

### 7.2 Future candidates (backlog)

- AuthN/AuthZ for API and Gradio
- Multi-category / multi-index support
- Semantic (fuzzy) caching
- User feedback loop wired to evaluation datasets
- Webhook-mode Telegram at scale
- Persistent Telegram session store (Redis/Postgres)
- Alternative embedding providers (local sentence-transformers only)
- Paper recommendation / “new papers this week” digests
- Slack / Discord adapters

---

## 8. Success metrics

| Metric | Target (v1) | How measured |
|--------|-------------|--------------|
| Ingestion success rate | ≥ 95% of scheduled DAG runs succeed | Airflow |
| Search availability | Health green when OpenSearch up | `/health` + OpenSearch cluster health |
| Citation presence | ≥ 90% of in-scope RAG answers include ≥ 1 source | Manual / eval set |
| Cache benefit | Repeated identical queries ≪ first-query latency | Redis + Langfuse |
| Guardrail behavior | Obvious out-of-domain queries refused | Agentic eval cases |
| Developer time-to-first-answer | < 30 min on a machine meeting prerequisites | Setup checklist |

---

## 9. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Weak small local LLM answers | Low answer quality | Allow larger Ollama models; keep retrieval strong |
| Embedding API outage | Hybrid degraded | Auto-fallback to BM25 |
| Disk growth from PDFs | Host fills up | PDF cache cleanup task; configurable limits |
| arXiv rate limits | Ingestion delays | Rate limiting + retries in client |
| Hallucinated citations | Trust loss | Prompting + only return sources from retrieved hits |
| Telegram token leak | Abuse | Env-only secrets; optional user allowlist |

---

## 10. Dependencies and assumptions

### Dependencies

- arXiv public API availability
- Jina embeddings API (for hybrid mode)
- Docker runtime on the host
- Ollama model pulled for configured `OLLAMA_MODEL`

### Assumptions

- Operator can allocate ≥ 8GB RAM to Docker
- Primary corpus is English CS/AI arXiv papers
- Single-operator / small-team deployment (not multi-tenant SaaS)
- Default category `cs.AI` is acceptable unless overridden

---

## 11. Open questions

1. Should v1.1 add API authentication by default?
2. Preferred default Ollama model for quality vs. resource tradeoff?
3. Should Telegram be enabled in Compose by default or remain opt-in?
4. Target corpus size / retention policy for indexed papers?

---

## 12. Document control

| Role | Responsibility |
|------|----------------|
| Product owner | Prioritize backlog, accept release scope |
| Engineering | Implement against PRD + TRD |
| Operator | Deploy, configure secrets, monitor DAGs |

**Related documents**

- [README](../README.md) — setup and overview  
- [TRD](TRD.md) — technical requirements and design  
- [LICENSE](../LICENSE) — no open-source license; all rights reserved  
