"""Application configuration using pydantic-settings."""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Settings
    app_name: str = "GovSearch API"
    app_version: str = "1.0.0"
    app_description: str = "Semantic and keyword search API for government websites"
    debug: bool = False

    # CORS Settings
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # OpenSearch Settings
    opensearch_host: str = "http://localhost:9200"
    opensearch_index: str = "govsites"
    opensearch_timeout: int = 30
    opensearch_http_compress: bool = True

    # Embedding Model Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Search Settings
    default_search_size: int = 10
    max_search_size: int = 100
    default_keyword_weight: float = 0.6
    default_chunks_to_return: int = 3
    knn_k: int = 5


settings = Settings()
