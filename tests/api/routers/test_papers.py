from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4


def _paper() -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        arxiv_id="2401.00001",
        title="Attention is all you need",
        authors=["Ashish Vaswani"],
        abstract="A paper abstract.",
        categories=["cs.AI"],
        published_date=now,
        pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
        raw_text="Extracted text",
        sections=None,
        references=None,
        parser_used="docling",
        parser_metadata=None,
        pdf_processed=True,
        pdf_processing_date=now,
        created_at=now,
        updated_at=now,
    )


async def test_list_papers(client):
    paper = _paper()
    with (
        patch("src.routers.papers.PaperRepository.get_all", return_value=[paper]),
        patch("src.routers.papers.PaperRepository.get_count", return_value=1),
    ):
        response = await client.get("/api/v1/papers/")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["papers"][0]["arxiv_id"] == "2401.00001"
    assert body["papers"][0]["title"] == "Attention is all you need"


async def test_get_paper_not_found(client):
    response = await client.get("/api/v1/papers/2401.00001")
    assert response.status_code == 404
