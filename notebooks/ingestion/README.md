# Paper ingestion

Fetches arXiv papers, reads the PDFs with Docling, and stores the records in PostgreSQL. A PDF longer than 30 pages is stored from the abstract.

<p align="center">
  <img src="../../static/data_ingestion_flow.png" alt="Paper ingestion flow" width="800">
</p>

Open `arxiv_ingestion.ipynb`.
