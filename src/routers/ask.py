from fastapi import APIRouter
from src.schemas.ask import AskRequest, AskResponse, PaperSource

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """
    Placeholder question-answering endpoint.

    Returns mock data until retrieval and generation are wired.
    """
    mock_sources = [
        PaperSource(
            arxiv_id="2401.00001",
            title="Mock Paper: Introduction to AI Research",
            authors=["John Doe", "Jane Smith"],
            abstract_preview="This is a mock abstract for API contract testing...",
        ),
        PaperSource(
            arxiv_id="2401.00002",
            title="Mock Paper: Advanced Machine Learning Techniques",
            authors=["Alice Johnson", "Bob Wilson"],
            abstract_preview="Another mock abstract demonstrating the API structure...",
        ),
    ]

    return AskResponse(
        answer="This is a placeholder response. Retrieval and generation will be implemented next.",
        sources=mock_sources,
    )
