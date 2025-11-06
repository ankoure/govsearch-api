"""Response models for API endpoints."""

from typing import List, Optional

from pydantic import BaseModel


class GISLink(BaseModel):
    """GIS link model."""
    url: str
    text: str


class Chunk(BaseModel):
    """Document chunk with embedding."""
    text: str
    keywords: Optional[List[str]] = None
    score: Optional[float] = None

class BucketInfo(BaseModel):
    """Aggregation bucket information."""
    name: str
    count: int


class SearchResult(BaseModel):
    """Individual search result."""
    url: str
    title: str
    snippet: str
    score: float
    source_name: Optional[str] = None
    domain: Optional[str] = None
    keywords: Optional[List[str]] = None
    crawled_at: Optional[str] = None
    matched_chunks: Optional[List[Chunk]] = None


class SearchResponse(BaseModel):
    """Search response with results and metadata."""
    total: int
    results: List[SearchResult]
    took_ms: int


class SourceInfo(BaseModel):
    """Source information with document count."""
    source_name: str
    doc_count: int


class SourcesResponse(BaseModel):
    """Response containing list of sources."""
    sources: List[SourceInfo]
    total: int


class StatsResponse(BaseModel):
    """Index statistics response."""
    total_documents: int
    sources: List[BucketInfo]
    domains: List[BucketInfo]
    status: List[BucketInfo]
