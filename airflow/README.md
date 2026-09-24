# Airflow

Apache Airflow config and DAGs for Research Agent paper ingestion.

<p align="center">
  <img src="../static/data_ingestion_flow.png" alt="Paper ingestion flow" width="800">
</p>

## DAGs

- **`hello_world_dag.py`** — smoke test that Airflow can reach the API and Postgres  
- **`arxiv_paper_ingestion.py`** — weekday pipeline: fetch, parse, store, report, cleanup  

```
airflow/
├── README.md
├── Dockerfile
├── entrypoint.sh
├── requirements-airflow.txt
└── dags/
    ├── hello_world_dag.py
    ├── arxiv_paper_ingestion.py
    └── arxiv_ingestion/
        └── tasks.py
```

## Ingestion pipeline

1. Set up environment and verify services  
2. Fetch papers from arXiv for the target date  
3. Download and parse PDFs with Docling  
4. Retry failed PDFs  
5. Record OpenSearch placeholders (indexing comes later)  
6. Generate a daily report  
7. Clean PDFs older than 30 days under `/tmp`  

Schedule: Monday–Friday at 06:00 UTC (`0 6 * * 1-5`). Trigger manually from the UI for a backfill.

## Access

- UI: http://localhost:8080  
- Credentials: `airflow/simple_auth_manager_passwords.json.generated` after first start  

## Notes

- Source is mounted at `/opt/airflow/src` so DAG tasks reuse application services  
- Rate limiting follows arXiv etiquette (about 3 seconds between requests)  
- Docling, poppler, and tesseract are installed in the Airflow image  
