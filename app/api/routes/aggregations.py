"""Aggregation endpoints for statistics and sources."""


from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_opensearch_client
from app.core.config import settings
from app.models.responses import StatsResponse, BucketInfo, SourceInfo, SourcesResponse
from opensearchpy import OpenSearch

router = APIRouter(tags=["Aggregations"])


@router.get("/sources", response_model=SourcesResponse)
def get_sources(
    limit: int = Query(50, ge=1, le=500),
    client: OpenSearch = Depends(get_opensearch_client),
) -> SourcesResponse:
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
                SourceInfo(source_name=bucket["key"], doc_count=bucket["doc_count"])
            )

    return SourcesResponse(sources=sources, total=len(sources))


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    client: OpenSearch = Depends(get_opensearch_client),
) -> StatsResponse:
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

        return StatsResponse(
            total_documents=count_result["count"],
            sources=[
                BucketInfo(name=b["key"], count=b["doc_count"])
                for b in agg_results["aggregations"]["sources"]["buckets"]
            ],
            domains=[
                BucketInfo(name=b["key"], count=b["doc_count"])
                for b in agg_results["aggregations"]["domains"]["buckets"]
            ],
            status=[
                BucketInfo(name=b["key"], count=b["doc_count"])
                for b in agg_results["aggregations"]["status"]["buckets"]
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
