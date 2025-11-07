"""FastAPI dependencies."""

from typing import Generator

from opensearchpy import OpenSearch

from app.core.config import settings
from app.services.ollama import OllamaService, ollama_service
from app.services.search import SearchService

# Global OpenSearch client
_opensearch_client: OpenSearch | None = None


def get_opensearch_client() -> OpenSearch:
    """
    Get or create OpenSearch client singleton.

    Returns:
        OpenSearch client instance
    """
    global _opensearch_client
    if _opensearch_client is None:
        _opensearch_client = OpenSearch(
            hosts=[settings.opensearch_host],
            http_compress=settings.opensearch_http_compress,
            timeout=settings.opensearch_timeout,
        )
    return _opensearch_client


def get_search_service() -> Generator[SearchService, None, None]:
    """
    Dependency for getting search service.

    Yields:
        SearchService instance
    """
    client = get_opensearch_client()
    yield SearchService(client)


def get_ollama_service() -> OllamaService:
    """
    Get Ollama service singleton.

    Returns:
        OllamaService instance
    """
    return ollama_service
