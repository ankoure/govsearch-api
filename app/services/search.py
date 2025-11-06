"""Search service for OpenSearch operations."""

from typing import Any, Dict, Optional

from opensearchpy import OpenSearch

from app.core.config import settings
from app.models.responses import Chunk, SearchResult, SearchResponse
from app.services.embedder import embedder_service


class SearchService:
    """Service for handling search operations."""

    def __init__(self, client: OpenSearch) -> None:
        """
        Initialize search service.

        Args:
            client: OpenSearch client instance
        """
        self.client = client
        self.index = settings.opensearch_index

    def hybrid_search(
        self,
        query: str,
        k: int,
        use_semantic: bool,
        source: Optional[str],
        keyword_weight: float,
    ) -> SearchResponse:
        """
        Perform hybrid search combining BM25 and semantic search.

        Args:
            query: Search query string
            k: Number of results to return
            use_semantic: Whether to use semantic search
            source: Optional source filter
            keyword_weight: Weight for keyword score (0-1)

        Returns:
            SearchResponse with results
        """
        # Build keyword query
        must_queries = [
            {"multi_match": {"query": query, "fields": ["title^2", "text"]}}
        ]

        filters = []
        if source:
            filters.append({"term": {"source_name": source}})

        keyword_query = {"bool": {"must": must_queries, "filter": filters}}

        # Execute keyword search
        results_keyword = self.client.search(
            index=self.index,
            body={
                "size": k,
                "query": keyword_query,
                "_source": [
                    "url",
                    "title",
                    "text",
                    "source_name",
                    "domain",
                    "keywords",
                    "crawled_at",
                ],
            },
        )

        hits: Dict[str, Any] = {}
        for hit in results_keyword["hits"]["hits"]:
            hits[hit["_id"]] = {"score": hit["_score"], "source": hit["_source"]}

        # Semantic search if enabled
        if use_semantic:
            query_vector = embedder_service.embed_text(query)

            semantic_body: Dict[str, Any] = {
                "size": k,
                "query": {
                    "nested": {
                        "path": "chunks",
                        "query": {
                            "knn": {
                                "chunks.vector": {
                                    "vector": query_vector,
                                    "k": settings.knn_k,
                                }
                            }
                        },
                        "inner_hits": {
                            "size": settings.default_chunks_to_return,
                            "_source": ["chunks.text", "chunks.keywords"],
                        },
                    }
                },
                "_source": [
                    "url",
                    "title",
                    "text",
                    "source_name",
                    "domain",
                    "keywords",
                    "crawled_at",
                ],
            }

            if source:
                semantic_body["query"] = {
                    "bool": {"must": [semantic_body["query"]], "filter": filters}
                }

            results_semantic = self.client.search(index=self.index, body=semantic_body)

            # Merge results
            semantic_weight = 1.0 - keyword_weight
            for hit in results_semantic["hits"]["hits"]:
                _id = hit["_id"]
                s = hit["_score"]

                matched_chunks = []
                if "inner_hits" in hit and "chunks" in hit["inner_hits"]:
                    for chunk_hit in hit["inner_hits"]["chunks"]["hits"]["hits"]:
                        matched_chunks.append(
                            {
                                "text": chunk_hit["_source"]["text"],
                                "keywords": chunk_hit["_source"].get("keywords", []),
                                "score": chunk_hit["_score"],
                            }
                        )

                if _id in hits:
                    hits[_id]["score"] = (
                        keyword_weight * hits[_id]["score"] + semantic_weight * s
                    )
                    hits[_id]["matched_chunks"] = matched_chunks
                else:
                    hits[_id] = {
                        "score": semantic_weight * s,
                        "source": hit["_source"],
                        "matched_chunks": matched_chunks,
                    }

        # Sort and format results
        ranked = sorted(hits.items(), key=lambda x: x[1]["score"], reverse=True)

        results = []
        for _id, data in ranked[:k]:
            src = data["source"]
            snippet = src.get("text", "")[:300]
            if len(src.get("text", "")) > 300:
                snippet += "..."

            result = SearchResult(
                url=src.get("url", ""),
                title=src.get("title", ""),
                snippet=snippet,
                score=round(data["score"], 3),
                source_name=src.get("source_name"),
                domain=src.get("domain"),
                keywords=src.get("keywords"),
                crawled_at=src.get("crawled_at"),
                matched_chunks=(
                    [Chunk(**c) for c in data.get("matched_chunks", [])]
                    if "matched_chunks" in data
                    else None
                ),
            )
            results.append(result)

        return SearchResponse(
            total=results_keyword["hits"]["total"]["value"],
            results=results,
            took_ms=results_keyword["took"],
        )

    def keyword_search(
        self, query: str, k: int, source: Optional[str]
    ) -> SearchResponse:
        """
        Perform pure keyword (BM25) search.

        Args:
            query: Search query string
            k: Number of results to return
            source: Optional source filter

        Returns:
            SearchResponse with results
        """
        must_queries = [
            {"multi_match": {"query": query, "fields": ["title^2", "text"]}}
        ]

        query_body: Dict[str, Any] = {
            "size": k,
            "query": {"bool": {"must": must_queries}},
            "_source": [
                "url",
                "title",
                "text",
                "source_name",
                "domain",
                "keywords",
                "crawled_at",
            ],
        }

        if source:
            query_body["query"]["bool"]["filter"] = [{"term": {"source_name": source}}]

        results = self.client.search(index=self.index, body=query_body)

        search_results = []
        for hit in results["hits"]["hits"]:
            src = hit["_source"]
            snippet = src.get("text", "")[:300]
            if len(src.get("text", "")) > 300:
                snippet += "..."

            search_results.append(
                SearchResult(
                    url=src.get("url", ""),
                    title=src.get("title", ""),
                    snippet=snippet,
                    score=round(hit["_score"], 3),
                    source_name=src.get("source_name"),
                    domain=src.get("domain"),
                    keywords=src.get("keywords"),
                    crawled_at=src.get("crawled_at"),
                )
            )

        return SearchResponse(
            total=results["hits"]["total"]["value"],
            results=search_results,
            took_ms=results["took"],
        )

    def semantic_search(
        self, query: str, k: int, source: Optional[str]
    ) -> SearchResponse:
        """
        Perform pure semantic/vector search.

        Args:
            query: Search query string
            k: Number of results to return
            source: Optional source filter

        Returns:
            SearchResponse with results
        """
        query_vector = embedder_service.embed_text(query)

        query_body: Dict[str, Any] = {
            "size": k,
            "query": {
                "nested": {
                    "path": "chunks",
                    "query": {
                        "knn": {
                            "chunks.vector": {
                                "vector": query_vector,
                                "k": settings.knn_k,
                            }
                        }
                    },
                    "inner_hits": {
                        "size": settings.default_chunks_to_return,
                        "_source": ["chunks.text", "chunks.keywords"],
                    },
                }
            },
            "_source": [
                "url",
                "title",
                "text",
                "source_name",
                "domain",
                "keywords",
                "crawled_at",
            ],
        }

        if source:
            query_body["query"] = {
                "bool": {
                    "must": [query_body["query"]],
                    "filter": [{"term": {"source_name": source}}],
                }
            }

        results = self.client.search(index=self.index, body=query_body)

        search_results = []
        for hit in results["hits"]["hits"]:
            src = hit["_source"]

            matched_chunks = []
            if "inner_hits" in hit and "chunks" in hit["inner_hits"]:
                for chunk_hit in hit["inner_hits"]["chunks"]["hits"]["hits"]:
                    matched_chunks.append(
                        Chunk(
                            text=chunk_hit["_source"]["text"],
                            keywords=chunk_hit["_source"].get("keywords", []),
                            score=chunk_hit["_score"],
                        )
                    )

            snippet = (
                matched_chunks[0].text[:300]
                if matched_chunks
                else src.get("text", "")[:300]
            )
            if len(snippet) == 300:
                snippet += "..."

            search_results.append(
                SearchResult(
                    url=src.get("url", ""),
                    title=src.get("title", ""),
                    snippet=snippet,
                    score=round(hit["_score"], 3),
                    source_name=src.get("source_name"),
                    domain=src.get("domain"),
                    keywords=src.get("keywords"),
                    crawled_at=src.get("crawled_at"),
                    matched_chunks=matched_chunks,
                )
            )

        return SearchResponse(
            total=results["hits"]["total"]["value"],
            results=search_results,
            took_ms=results["took"],
        )
