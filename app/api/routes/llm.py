"""LLM-powered endpoints using Ollama."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_ollama_service, get_search_service
from app.core.config import settings
from app.models.responses import (
    AnswerRequest,
    AnswerResponse,
    ChatRequest,
    ChatResponse,
    LLMAvailabilityResponse,
    SearchResult,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.ollama import OllamaService
from app.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/status", response_model=LLMAvailabilityResponse)
async def llm_status(
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> LLMAvailabilityResponse:
    """
    Check if LLM service is available.

    Returns:
        LLM availability status with model information
    """
    if ollama_service.is_available():
        return LLMAvailabilityResponse(
            available=True,
            model=ollama_service.model,
            host=ollama_service.client.host if ollama_service.client else None,  # type: ignore
        )
    return LLMAvailabilityResponse(available=False)


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_search(
    request: SummarizeRequest,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> SummarizeResponse:
    """
    Search for a query and generate a summary of the top results.

    This endpoint:
    1. Performs a hybrid search for the query
    2. Extracts key content from top results
    3. Uses LLM to generate a comprehensive summary

    Args:
        request: Query and max results to summarize

    Returns:
        Summary with source attribution
    """
    if not ollama_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="LLM service is not available. Please enable Ollama in configuration.",
        )

    # Perform hybrid search
    search_response = search_service.hybrid_search(
        query=request.query,
        k=request.max_results,
        use_semantic=True,
        source=None,
        keyword_weight=settings.default_keyword_weight,
    )

    if not search_response.results:
        raise HTTPException(
            status_code=404,
            detail="No results found for the query.",
        )

    # Prepare context from search results
    context_parts = []
    for i, result in enumerate(search_response.results, 1):
        context_parts.append(f"Source {i}: {result.title}\n{result.snippet}")
        if result.matched_chunks:
            for chunk in result.matched_chunks[:2]:  # Top 2 chunks per result
                context_parts.append(f"  - {chunk.text}")

    context = "\n\n".join(context_parts)

    # Generate summary
    prompt = f"""Based on the following search results about "{request.query}", provide a comprehensive summary that synthesizes the key information. Include relevant details and mention if there are different perspectives or aspects covered.
    {context}

    Summary:"""

    summary = ollama_service.generate(prompt)

    if not summary:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate summary from LLM.",
        )

    return SummarizeResponse(
        query=request.query,
        summary=summary,
        sources_used=len(search_response.results),
        sources=search_response.results,
    )


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(
    request: AnswerRequest,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> AnswerResponse:
    """
    Answer a question using RAG (Retrieval-Augmented Generation).

    This endpoint:
    1. Searches for relevant documents using hybrid search
    2. Extracts the most relevant chunks
    3. Uses LLM to answer the question based on the context

    Args:
        request: Question and search parameters

    Returns:
        Answer with source attribution and confidence
    """
    if not ollama_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="LLM service is not available. Please enable Ollama in configuration.",
        )

    # Perform hybrid search
    search_response = search_service.hybrid_search(
        query=request.question,
        k=request.max_results,
        use_semantic=True,
        source=request.source_filter,
        keyword_weight=settings.default_keyword_weight,
    )

    if not search_response.results:
        raise HTTPException(
            status_code=404,
            detail="No relevant documents found for the question.",
        )

    # Extract chunks for context
    chunks = []
    for result in search_response.results:
        if result.matched_chunks:
            for chunk in result.matched_chunks:
                chunks.append(f"{result.title}: {chunk.text}")
        else:
            chunks.append(f"{result.title}: {result.snippet}")

    # Generate answer
    answer = ollama_service.answer_question(
        question=request.question,
        context_chunks=chunks,
    )

    if not answer:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate answer from LLM.",
        )

    # Determine confidence based on number of sources and answer content
    confidence = "high"
    if len(search_response.results) < 2:
        confidence = "low"
    elif len(search_response.results) < 4:
        confidence = "medium"
    elif "cannot find" in answer.lower() or "don't know" in answer.lower():
        confidence = "low"

    return AnswerResponse(
        question=request.question,
        answer=answer,
        sources=search_response.results,
        confidence=confidence,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_context(
    request: ChatRequest,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> ChatResponse:
    """
    Chat with the LLM, optionally with context from documents.

    This endpoint:
    1. Optionally searches for relevant context if context_query is provided
    2. Uses chat format to have a conversation with the LLM
    3. Returns response with source attribution if context was used

    Args:
        request: Chat message and optional context query

    Returns:
        Chat response with optional source attribution
    """
    if not ollama_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="LLM service is not available. Please enable Ollama in configuration.",
        )

    sources: list[SearchResult] = []
    context_used = False
    system_message = "You are a helpful assistant that answers questions about government information and documents."

    # If context query provided, search for relevant documents
    if request.context_query:
        search_response = search_service.hybrid_search(
            query=request.context_query,
            k=request.max_context_results,
            use_semantic=True,
            source=None,
            keyword_weight=settings.default_keyword_weight,
        )

        if search_response.results:
            context_used = True
            sources = search_response.results

            # Build context
            context_parts = []
            for result in search_response.results:
                context_parts.append(f"Source: {result.title}\n{result.snippet}")
                if result.matched_chunks:
                    for chunk in result.matched_chunks[:1]:
                        context_parts.append(f"  {chunk.text}")

            context = "\n\n".join(context_parts)
            system_message = f"""You are a helpful assistant that answers questions about government information and documents.

            Here is some relevant context from government documents:

            {context}

            Use this context to help answer the user's question, but you can also use your general knowledge. If the context is relevant, reference it in your answer."""

    # Build messages for chat
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": request.message},
    ]

    # Get chat response
    chat_response = ollama_service.chat(messages=messages)

    if not chat_response:
        raise HTTPException(
            status_code=500,
            detail="Failed to get response from LLM.",
        )

    response_text = chat_response["message"]["content"]

    return ChatResponse(
        message=request.message,
        response=response_text,
        context_used=context_used,
        sources=sources if context_used else None,
    )
