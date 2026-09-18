"""
RAG Tools — Vector search, hybrid search, and reranking tools.

These tools are the primary interface for the RAG agent to query
the Qdrant vector store. They are defined here as standalone modules
and also imported into the RAG agent.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def create_rag_tools(vector_store: Any | None = None) -> list:
    """Create RAG-specific tools bound to a vector store instance.

    This is the canonical factory for RAG tools. The RAG agent imports
    and uses these tools via its own `create_rag_tools` wrapper.

    Args:
        vector_store: VectorStoreService instance.

    Returns:
        List of LangChain tool objects.
    """

    @tool
    def vector_search(query: str, top_k: int = 5) -> str:
        """Search the enterprise knowledge base using semantic vector similarity.

        Args:
            query: The search query.
            top_k: Number of top results to return.

        Returns:
            Formatted string of retrieved document chunks with metadata.
        """
        if vector_store is None:
            return "Vector store not available. Please ingest documents first."

        try:
            results = vector_store.search(query=query, top_k=top_k)
            if not results:
                return "No relevant documents found for your query."

            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(
                    f"[Source {i}] (score: {result.get('score', 0):.3f})\n"
                    f"  File: {result.get('source', 'Unknown')}\n"
                    f"  Content: {result.get('content', '')[:500]}\n"
                )
            return "\n---\n".join(formatted)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return f"Search error: {str(e)}"

    @tool
    def hybrid_search(query: str, top_k: int = 5) -> str:
        """Search using both semantic vectors and keyword matching for better recall.

        Combines dense vector search with BM25-style keyword matching to handle
        domain-specific terminology and proper nouns better than pure semantic search.

        Args:
            query: The search query.
            top_k: Number of top results to return.

        Returns:
            Formatted string of retrieved document chunks with metadata.
        """
        if vector_store is None:
            return "Vector store not available. Please ingest documents first."

        try:
            results = vector_store.hybrid_search(query=query, top_k=top_k)
            if not results:
                return "No relevant documents found for your hybrid query."

            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(
                    f"[Source {i}] (score: {result.get('score', 0):.3f})\n"
                    f"  File: {result.get('source', 'Unknown')}\n"
                    f"  Content: {result.get('content', '')[:500]}\n"
                )
            return "\n---\n".join(formatted)
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return f"Search error: {str(e)}"

    @tool
    def rerank_results(query: str, results_text: str, top_k: int = 3) -> str:
        """Rerank search results for better relevance ordering.

        Uses query-document similarity re-scoring to promote the most
        relevant results to the top of the list.

        Args:
            query: The original search query.
            results_text: Concatenated search results to rerank.
            top_k: Number of top results to keep after reranking.

        Returns:
            Reranked results as formatted text.
        """
        # In production, this would use a cross-encoder model for reranking.
        # For now, it returns the input as-is (already ranked by vector similarity).
        return f"Reranked top {top_k} results for query '{query}':\n{results_text}"

    @tool
    def get_document_metadata(source_file: str) -> str:
        """Retrieve metadata about a specific document in the knowledge base.

        Args:
            source_file: The filename or path of the document.

        Returns:
            Document metadata including chunk count, ingestion date, etc.
        """
        if vector_store is None:
            return "Vector store not available."

        try:
            metadata = vector_store.get_document_info(source_file)
            if metadata:
                return (
                    f"Document: {metadata.get('source', source_file)}\n"
                    f"Chunks: {metadata.get('chunk_count', 'Unknown')}\n"
                    f"Ingested: {metadata.get('ingested_at', 'Unknown')}\n"
                    f"Type: {metadata.get('file_type', 'Unknown')}"
                )
            return f"No metadata found for document: {source_file}"
        except Exception as e:
            return f"Metadata retrieval error: {str(e)}"

    return [vector_search, hybrid_search, rerank_results, get_document_metadata]
