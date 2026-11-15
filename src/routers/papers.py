from fastapi import APIRouter, HTTPException, Path, Query
from src.dependencies import SessionDep
from src.repositories.paper import PaperRepository
from src.schemas.arxiv.paper import PaperResponse, PaperSearchResponse

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("/", response_model=PaperSearchResponse)
def list_papers(
    db: SessionDep,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaperSearchResponse:
    """List papers stored in PostgreSQL."""
    paper_repo = PaperRepository(db)
    papers = paper_repo.get_all(limit=limit, offset=offset)
    total = paper_repo.get_count()
    return PaperSearchResponse(
        papers=[PaperResponse.model_validate(paper) for paper in papers],
        total=total,
    )


@router.get("/{arxiv_id}", response_model=PaperResponse)
def get_paper(
    db: SessionDep,
    arxiv_id: str = Path(pattern=r"^\d{4}\.\d{4,5}(v\d+)?$"),
) -> PaperResponse:
    """Return one stored paper by arXiv id."""
    paper = PaperRepository(db).get_by_arxiv_id(arxiv_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperResponse.model_validate(paper)
