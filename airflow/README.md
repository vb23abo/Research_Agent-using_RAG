# Airflow

Weekday pipeline for fetching arXiv papers, reading PDFs, and indexing them for hybrid search.

<p align="center">
  <img src="../static/data_ingestion_flow.png" alt="Paper ingestion flow" width="800">
</p>

## DAGs

- `hello_world_dag.py` checks that Airflow can reach the API and PostgreSQL.
- `arxiv_paper_ingestion.py` runs Monday to Friday at 06:00 UTC.

```
airflow/
├── Dockerfile
├── entrypoint.sh
├── requirements-airflow.txt
└── dags/
    ├── hello_world_dag.py
    ├── arxiv_paper_ingestion.py
    └── arxiv_ingestion/
        ├── common.py
        ├── setup.py
        ├── fetching.py
        ├── indexing.py
        └── reporting.py
```

## Pipeline

1. Check PostgreSQL, the arXiv client, and the PDF parser.
2. Fetch `cs.AI` papers and store the parsed text.
3. Chunk the text, embed it, and index it in OpenSearch.
4. Write a short report and delete PDFs under `/tmp` that are older than 30 days.

The UI is at http://localhost:8080. The first start creates an admin user with username `admin` and password `admin`.

On 26 November 2026, `fetch_daily_papers` and `index_papers_hybrid` were run directly, with `max_results` set to 1, for the `cs.AI` papers of 25 November 2026. Paper `2611.34942` was parsed, stored, and indexed as 12 chunks. The Airflow scheduler was not started for that check. A PDF over 30 pages is stored from the abstract.
