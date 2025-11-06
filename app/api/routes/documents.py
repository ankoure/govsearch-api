"""Document retrieval endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_opensearch_client
from app.core.config import settings
from opensearchpy import OpenSearch

router = APIRouter(prefix="/document", tags=["Documents"])


@router.get("/{doc_id}")
def get_document(
    doc_id: str,
    client: OpenSearch = Depends(get_opensearch_client),
) -> Dict[str, Any]:
    """
    Retrieve a specific document by its ID.
    """
    try:
        result = client.get(index=settings.opensearch_index, id=doc_id)
        return result["_source"]
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found: {str(e)}")
