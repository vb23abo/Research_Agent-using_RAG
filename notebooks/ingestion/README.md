# Paper ingestion

Guides for fetching arXiv papers, parsing PDFs, and storing them in PostgreSQL.

## Contents

### `arxiv_ingestion.ipynb`

Interactive walkthrough of:

1. **Service checks** — confirm API, Postgres, Airflow, and Ollama are up  
2. **arXiv client** — rate-limited fetch with retries and date filters  
3. **PDF processing** — download, cache, and parse with Docling  
4. **Database writes** — upsert paper metadata and extracted text  
5. **End-to-end run** — fetch → parse → store  

<p align="center">
  <img src="../../static/data_ingestion_flow.png" alt="Paper ingestion flow" width="800">
</p>

**Pipeline**

```
arXiv query → rate-limited fetch → PDF download → Docling parse → PostgreSQL
```

| Component | Role |
|-----------|------|
| `ArxivClient` | Fetch CS.AI papers with 3s rate limiting |
| `PDFParserService` | Structured extraction from scientific PDFs |
| `MetadataFetcher` | Orchestrate download, parse, and store |
| `PaperRepository` | Upsert papers in PostgreSQL |
| Airflow DAG `arxiv_paper_ingestion` | Weekday scheduled run |

## Rebuild after this change

```bash
docker compose down
docker compose up --build -d
```

New Airflow/PDF dependencies need a rebuild, not a cached restart.

## Troubleshooting

1. Confirm `make health` / `docker compose ps`  
2. If the `papers` table is missing new columns, recreate volumes (`docker compose down -v`)  
3. Check Airflow DAG logs at http://localhost:8080  
4. Respect arXiv rate limits if fetches fail with 429  
