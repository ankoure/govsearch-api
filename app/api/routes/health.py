"""Health check endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_opensearch_client
from opensearchpy import OpenSearch

router = APIRouter(tags=["Health"])


@router.get("/")
def health_check(
    client: OpenSearch = Depends(get_opensearch_client),
) -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        info = client.info()
        return {
            "status": "healthy",
            "opensearch_cluster": info.get("cluster_name"),
            "version": info.get("version", {}).get("number"),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"OpenSearch unavailable: {str(e)}")
