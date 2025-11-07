"""Ollama LLM service for text generation and chat."""

import logging
from typing import List, Optional

import ollama
from ollama import ChatResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for interacting with Ollama LLM."""

    def __init__(self) -> None:
        """Initialize the Ollama service."""
        self.enabled = settings.ollama_enabled
        self.client: Optional[ollama.Client] = None
        self.model = settings.ollama_model

        if self.enabled:
            try:
                self.client = ollama.Client(host=settings.ollama_host)
                # Test connection
                self.client.list()
                logger.info(f"Ollama service initialized with model: {self.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama client: {e}")
                self.enabled = False
                self.client = None

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        return self.enabled and self.client is not None

    def generate(self, prompt: str, context: Optional[str] = None) -> Optional[str]:
        """
        Generate text using Ollama.

        Args:
            prompt: The prompt to generate from
            context: Optional context to include

        Returns:
            Generated text or None if service unavailable
        """
        if not self.is_available():
            logger.warning("Ollama service not available")
            return None

        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt

            response = self.client.generate(  # type: ignore
                model=self.model,
                prompt=full_prompt,
                options={
                    "num_ctx": settings.ollama_context_window,
                },
            )

            result: str = response["response"]
            return result
        except Exception as e:
            logger.error(f"Error generating text with Ollama: {e}")
            return None

    def chat(
        self,
        messages: List[dict[str, str]],
        stream: bool = False,
    ) -> Optional[ChatResponse]:
        """
        Chat with Ollama using conversation format.

        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response

        Returns:
            Chat response or None if service unavailable
        """
        if not self.is_available():
            logger.warning("Ollama service not available")
            return None

        try:
            response: ChatResponse = self.client.chat(  # type: ignore
                model=self.model,
                messages=messages,
                stream=stream,
                options={
                    "num_ctx": settings.ollama_context_window,
                },
            )

            return response
        except Exception as e:
            logger.error(f"Error chatting with Ollama: {e}")
            return None

    def summarize_text(self, text: str, max_length: int = 200) -> Optional[str]:
        """
        Summarize a text passage.

        Args:
            text: The text to summarize
            max_length: Maximum length of summary in words

        Returns:
            Summary or None if service unavailable
        """
        prompt = f"""Please provide a concise summary of the following text in no more than {max_length} words:

        {text}

        Summary:"""

        return self.generate(prompt)

    def answer_question(
        self,
        question: str,
        context_chunks: List[str],
    ) -> Optional[str]:
        """
        Answer a question based on provided context chunks.

        Args:
            question: The question to answer
            context_chunks: List of text chunks to use as context

        Returns:
            Answer or None if service unavailable
        """
        # Limit context chunks to configured maximum
        max_chunks = settings.ollama_max_chunks_for_context
        limited_chunks = context_chunks[:max_chunks]

        context = "\n\n---\n\n".join(
            [f"Context {i+1}:\n{chunk}" for i, chunk in enumerate(limited_chunks)]
        )

        prompt = f"""Based on the following context from government documents, please answer the question. If the answer cannot be found in the context, say "I cannot find this information in the provided documents."

        {context}

        Question: {question}

        Answer:"""

        return self.generate(prompt)


# Singleton instance
ollama_service = OllamaService()
