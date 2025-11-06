# GovSearch API

A FastAPI-based search API for government websites with hybrid search capabilities ([BM25](https://www.geeksforgeeks.org/nlp/what-is-bm25-best-matching-25-algorithm/) + [semantic vector search](https://cloud.google.com/discover/what-is-semantic-search)).

## Features

- **Hybrid Search**: Combines BM25 keyword relevance with semantic vector search
- **Nested Chunk Search**: Searches within document chunks with 384-dim embeddings
- **Source Filtering**: Filter results by source_name
- **Aggregations**: Get statistics on sources, domains, and status
- **Type-Safe**: Uses Pydantic models for request/response validation
- **Modular Architecture**: Well-organized codebase with separation of concerns
- **Environment-Based Configuration**: Uses pydantic-settings for flexible config management

## Project Structure

```md
govsearch-frontend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app initialization
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # Shared dependencies
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── search.py        # Search endpoints
│   │       ├── aggregations.py  # Stats & sources
│   │       ├── documents.py     # Document retrieval
│   │       └── health.py        # Health check
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py            # Settings with pydantic-settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── responses.py         # Response models
│   └── services/
│       ├── __init__.py
│       ├── embedder.py          # Embedding service
│       └── search.py            # Search logic/service layer
├── tests/                       # Test directory
├── .env.example                 # Example environment variables
├── .gitignore
├── README.md
├── pyproject.toml
└── uv.lock
```

## OpenSearch Index Mapping

The API expects an OpenSearch index with the following structure:

```python
{
    "properties": {
        "url": {"type": "keyword"},
        "domain": {"type": "keyword"},
        "title": {"type": "text"},
        "text": {"type": "text"},
        "status": {"type": "keyword"},
        "crawled_at": {"type": "date"},
        "source_name": {"type": "keyword"},
        "keywords": {"type": "keyword"},
        "chunks": {
            "type": "nested",
            "properties": {
                "text": {"type": "text"},
                "keywords": {"type": "keyword"},
                "vector": {"type": "dense_vector", "dims": 384}
            }
        },
        "gis_links": {
            "type": "nested",
            "properties": {
                "url": {"type": "keyword"},
                "text": {"type": "text"}
            }
        },
        "osm_relation_id": {"type": "keyword"}
    }
}
```

## Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .
```

## Configuration

Copy [.env.example](.env.example) to `.env` and configure your settings:

```bash
cp .env.example .env
```

Key configuration options in `.env`:

```bash
# OpenSearch connection
OPENSEARCH_HOST=http://localhost:9200
OPENSEARCH_INDEX=govsites

# Embedding model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Search settings
DEFAULT_KEYWORD_WEIGHT=0.6
MAX_SEARCH_SIZE=100
```

See [app/core/config.py](app/core/config.py) for all available settings.

## Running the API

```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using uv
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

## API Endpoints

### Health Check

**GET /** - Check API and OpenSearch health

```bash
curl http://localhost:8000/
```

### Search Endpoints

#### Hybrid Search (Recommended)

**GET /search** - Combines BM25 and semantic search

Parameters:

- `q` (required): Search query
- `k` (default: 10): Number of results
- `use_semantic` (default: true): Enable semantic search
- `source` (optional): Filter by source_name
- `keyword_weight` (default: 0.6): Weight for keyword score (0-1)

```bash
curl "http://localhost:8000/search?q=building%20permits&k=5&source=nyc_gov"
```

#### Keyword Search

**GET /search/keyword** - Pure BM25 search

```bash
curl "http://localhost:8000/search/keyword?q=zoning%20regulations&k=10"
```

#### Semantic Search

**GET /search/semantic** - Pure vector similarity search

```bash
curl "http://localhost:8000/search/semantic?q=affordable%20housing&k=10"
```

### Aggregation Endpoints

#### Get Sources

**GET /sources** - List all available sources with document counts

```bash
curl "http://localhost:8000/sources?limit=50"
```

#### Get Statistics

**GET /stats** - Index statistics and aggregations

```bash
curl http://localhost:8000/stats
```

### Document Endpoints

#### Get Document by ID

**GET /document/{doc_id}** - Retrieve specific document

```bash
curl http://localhost:8000/document/abc123
```

## Response Format

Search endpoints return:

```json
{
  "total": 42,
  "took_ms": 15,
  "results": [
    {
      "url": "https://example.gov/page",
      "title": "Page Title",
      "snippet": "Text snippet...",
      "score": 12.345,
      "source_name": "example_gov",
      "domain": "example.gov",
      "keywords": ["keyword1", "keyword2"],
      "crawled_at": "2025-01-15T10:30:00Z",
      "matched_chunks": [
        {
          "text": "Relevant chunk text...",
          "keywords": ["keyword"],
          "score": 8.5
        }
      ]
    }
  ]
}
```

## Architecture

### Service Layer

The application uses a service layer pattern to separate business logic from API routes:

- **[EmbedderService](app/services/embedder.py)**: Handles text embedding using sentence-transformers
- **[SearchService](app/services/search.py)**: Encapsulates all search logic (keyword, semantic, hybrid)

### Dependency Injection

FastAPI's dependency injection is used throughout:

- **[get_opensearch_client()](app/api/deps.py)**: Provides singleton OpenSearch client
- **[get_search_service()](app/api/deps.py)**: Provides SearchService instance with injected client

This makes the code highly testable - you can easily mock dependencies in tests.

### Configuration Management

Uses `pydantic-settings` for type-safe configuration with environment variable support. All settings are defined in [app/core/config.py](app/core/config.py).

## Development

```bash
# Run tests
uv run python -m pytest

# Type checking
uv run mypy app/

# Linting
uv run ruff check .

# Format code
uv run ruff format .
```

## Embeddings

The API uses [sentence-transformers](https://www.sbert.net/) with the `all-MiniLM-L6-v2` model (384 dimensions) for semantic search.

To use a different model, set the `EMBEDDING_MODEL` environment variable:

```bash
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIM=384
```

Make sure your OpenSearch mapping's `chunks.vector` dims matches your embedding model's output dimension.

## Architecture Notes

1. **Nested Chunks**: Documents are split into chunks during indexing, each with its own embedding. The API searches these chunks and returns the most relevant ones via `inner_hits`.
2. **Hybrid Scoring**: The default hybrid search combines keyword and semantic scores with a weighted average (60% keyword, 40% semantic by default).
3. **CORS**: CORS is enabled for all origins in development. Configure `CORS_ORIGINS` in `.env` for production.
4. **Performance**: The API uses OpenSearch's native KNN search on nested vectors, which is optimized for large-scale vector search.
5. **Singleton Pattern**: The OpenSearch client and embedding model are singletons to avoid repeated initialization overhead.

## Testing

Create test files in the `tests/` directory. Example:

```python
# tests/test_search.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
```
