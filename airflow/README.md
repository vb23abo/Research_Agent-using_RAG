# Airflow

Apache Airflow config and DAGs for the Research Agent ingestion workflows.

## Current setup

- **`hello_world_dag.py`** — smoke-test DAG to confirm Airflow is healthy  
- **`init-db.sql`** — DB bootstrap helper  

```
airflow/
├── README.md
├── Dockerfile
├── entrypoint.sh
├── init-db.sql
├── requirements-airflow.txt
└── dags/
    └── hello_world_dag.py
```

## Access

- UI: http://localhost:8080  
- Credentials: see `airflow/simple_auth_manager_passwords.json.generated` after first start  

## Next

Paper fetch, PDF processing, and indexing DAGs will live under `dags/` as the pipeline grows.
