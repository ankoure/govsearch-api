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


class LLMAvailabilityResponse(BaseModel):
    """LLM service availability status."""
    available: bool
    model: Optional[str] = None
    host: Optional[str] = None


class SummarizeRequest(BaseModel):
    """Request to summarize search results."""
    query: str
    max_results: int = 5


class SummarizeResponse(BaseModel):
    """Response from summarization."""
    query: str
    summary: str
    sources_used: int
    sources: List[SearchResult]


class AnswerRequest(BaseModel):
    """Request to answer a question using RAG."""
    question: str
    max_results: int = 5
    source_filter: Optional[str] = None


class AnswerResponse(BaseModel):
    """Response from question answering."""
    question: str
    answer: str
    sources: List[SearchResult]
    confidence: str


class ChatRequest(BaseModel):
    """Request for chat with context."""
    message: str
    context_query: Optional[str] = None
    max_context_results: int = 3


class ChatResponse(BaseModel):
    """Response from chat."""
    message: str
    response: str
    context_used: bool
    sources: Optional[List[SearchResult]] = None
