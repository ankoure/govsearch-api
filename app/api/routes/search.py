"""Search endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_search_service
from app.core.config import settings
from app.models.responses import SearchResponse
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
def hybrid_search(
    q: str = Query(..., description="Search query", min_length=1),
    k: int = Query(
        settings.default_search_size,
        ge=1,
        le=settings.max_search_size,
        description="Number of results to return",
    ),
    use_semantic: bool = Query(True, description="Enable semantic/vector search"),
    source: Optional[str] = Query(None, description="Filter by source_name"),
    keyword_weight: float = Query(
        settings.default_keyword_weight,
        ge=0.0,
        le=1.0,
        description="Weight for keyword score (0-1)",
    ),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """
    Hybrid search combining:
    - BM25 keyword search on title/text fields
    - Semantic vector search on nested chunks (if enabled)

    Returns unified ranked results with optional filtering by source.
    """
    return search_service.hybrid_search(q, k, use_semantic, source, keyword_weight)


@router.get("/keyword", response_model=SearchResponse)
def keyword_search(
    q: str = Query(..., min_length=1),
    k: int = Query(settings.default_search_size, ge=1, le=settings.max_search_size),
    source: Optional[str] = Query(None, description="Filter by source_name"),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """
    Pure keyword (BM25) search on title and text fields.
    Optionally filter by source_name.
    """
    return search_service.keyword_search(q, k, source)


@router.get("/semantic", response_model=SearchResponse)
def semantic_search(
    q: str = Query(..., min_length=1),
    k: int = Query(settings.default_search_size, ge=1, le=settings.max_search_size),
    source: Optional[str] = Query(None, description="Filter by source_name"),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """
    Pure semantic/vector search using nested chunks.
    Returns documents with their most relevant chunks.
    """
    return search_service.semantic_search(q, k, source)
