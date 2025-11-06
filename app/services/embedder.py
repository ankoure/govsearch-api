"""Embedding service using sentence-transformers."""

from typing import List

from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbedderService:
    """Service for generating text embeddings."""

    def __init__(self) -> None:
        """Initialize the embedding model."""
        self.model = SentenceTransformer(settings.embedding_model)

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a text string.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        return self.model.encode(text).tolist()


# Singleton instance
embedder_service = EmbedderService()
