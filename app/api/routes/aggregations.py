"""Aggregation endpoints for statistics and sources."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_opensearch_client
from app.core.config import settings
from opensearchpy import OpenSearch

router = APIRouter(tags=["Aggregations"])


@router.get("/sources")
def get_sources(
    limit: int = Query(50, ge=1, le=500),
    client: OpenSearch = Depends(get_opensearch_client),
) -> Dict[str, Any]:
    """
    Get list of available sources with document counts.
    """
    results = client.search(
        index=settings.opensearch_index,
        body={
            "size": 0,
            "aggs": {"sources": {"terms": {"field": "source_name", "size": limit}}},
        },
    )

    sources = []
    if "aggregations" in results and "sources" in results["aggregations"]:
        for bucket in results["aggregations"]["sources"]["buckets"]:
            sources.append(
                {"source_name": bucket["key"], "doc_count": bucket["doc_count"]}
            )

    return {"sources": sources, "total": len(sources)}


@router.get("/stats")
def get_stats(
    client: OpenSearch = Depends(get_opensearch_client),
) -> Dict[str, Any]:
    """
    Get index statistics and aggregations.
    """
    try:
        # Get document count
        count_result = client.count(index=settings.opensearch_index)

        # Get aggregations
        agg_results = client.search(
            index=settings.opensearch_index,
            body={
                "size": 0,
                "aggs": {
                    "sources": {"terms": {"field": "source_name", "size": 20}},
                    "domains": {"terms": {"field": "domain", "size": 20}},
                    "status": {"terms": {"field": "status"}},
                },
            },
        )

        return {
            "total_documents": count_result["count"],
            "sources": [
                {"name": b["key"], "count": b["doc_count"]}
                for b in agg_results["aggregations"]["sources"]["buckets"]
            ],
            "domains": [
                {"name": b["key"], "count": b["doc_count"]}
                for b in agg_results["aggregations"]["domains"]["buckets"]
            ],
            "status": [
                {"name": b["key"], "count": b["doc_count"]}
                for b in agg_results["aggregations"]["status"]["buckets"]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
