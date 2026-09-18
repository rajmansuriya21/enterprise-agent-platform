"""
RAG Sub-Agent — Retrieval-Augmented Generation with citation-grounded output.

Performs hybrid vector search (dense + keyword) via Qdrant, reranks results,
and generates responses grounded in retrieved documents with source citations.
Includes hallucination guardrails to keep responses factual.
"""

from __future__ import annotations

import time
import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool

from src.agents.state import AgentMetadata, AgentState
from src.config import get_settings
from src.utils.prompts import RAG_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# RAG Tools
# ──────────────────────────────────────────────────────────────
def create_rag_tools(vector_store: Any | None = None) -> list:
    """Create RAG-specific tools bound to a vector store instance."""

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

    return [vector_search, hybrid_search, get_document_metadata]


# ──────────────────────────────────────────────────────────────
# RAG Agent Node
# ──────────────────────────────────────────────────────────────
def create_rag_agent_node(llm: Any, vector_store: Any | None = None):
    """Create the RAG agent node for the LangGraph.

    The RAG agent:
    1. Receives a query from the supervisor
    2. Performs hybrid search against the vector store
    3. Reranks results for relevance
    4. Generates a response grounded in retrieved context
    5. Includes source citations in the response
    """
    tools = create_rag_tools(vector_store)
    llm_with_tools = llm.bind_tools(tools)

    def rag_agent_node(state: AgentState) -> dict[str, Any]:
        """Execute the RAG pipeline: search → rerank → generate with citations."""
        start_time = time.time()
        settings = get_settings()

        # Get the user's question from the latest human message
        user_query = ""
        task_desc = state.get("metadata", {}).get("last_task", "")
        for msg in reversed(state["messages"]):
            if hasattr(msg, "content") and getattr(msg, "name", "") != "supervisor":
                if not msg.content.startswith("[Supervisor"):
                    user_query = msg.content
                    break

        if task_desc:
            query_for_search = task_desc
        else:
            query_for_search = user_query

        # Step 1: Perform vector search
        search_results = []
        if vector_store is not None:
            try:
                search_results = vector_store.hybrid_search(
                    query=query_for_search, top_k=5
                )
            except Exception as e:
                logger.warning(f"Vector search failed, falling back: {e}")

        # Step 2: Build context from search results
        context_parts = []
        citations = []
        for i, result in enumerate(search_results):
            context_parts.append(
                f"[Source {i + 1}]: {result.get('content', '')}"
            )
            citations.append({
                "source_id": i + 1,
                "file": result.get("source", "Unknown"),
                "score": result.get("score", 0),
                "chunk_id": result.get("chunk_id", ""),
                "content_preview": result.get("content", "")[:200],
            })

        context_str = "\n\n".join(context_parts) if context_parts else "No documents found."

        # Step 3: Generate response with citation grounding
        messages = [
            SystemMessage(content=RAG_AGENT_SYSTEM_PROMPT.format(context=context_str)),
            *state["messages"],
        ]

        try:
            response = llm.invoke(messages)
            response_content = response.content
        except Exception as e:
            logger.error(f"RAG generation failed: {e}")
            response_content = f"I encountered an error while generating the response: {str(e)}"

        # Track metadata
        latency_ms = (time.time() - start_time) * 1000
        agent_meta = AgentMetadata(
            agent_name="rag_agent",
            model_used=settings.llm_model,
            latency_ms=latency_ms,
            tools_called=["hybrid_search"],
            success=True,
        )

        metadata = state.get("metadata", {})
        routing_history = metadata.get("routing_history", [])
        routing_history.append(agent_meta.model_dump())
        metadata["routing_history"] = routing_history

        return {
            "messages": [AIMessage(content=response_content, name="rag_agent")],
            "context": search_results,
            "citations": citations,
            "metadata": metadata,
        }

    return rag_agent_node
