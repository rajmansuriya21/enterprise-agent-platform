"""
Qdrant Vector Store Service — High-performance vector retrieval pipeline.

Provides a clean wrapper around the Qdrant client with:
- Collection management (create, delete, list)
- Dense vector search (semantic similarity)
- Hybrid search (dense + sparse/keyword)
- Document upsert and deletion
- Connection pooling and graceful fallback
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Qdrant vector store service with hybrid search capabilities."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        settings = get_settings()
        self._url = url or settings.qdrant_url
        self._api_key = api_key or settings.qdrant_api_key
        self._collection_name = collection_name or settings.qdrant_collection_name
        self._client: Any | None = None
        self._embedding_model: Any | None = None

    # ── Client Management ────────────────────────────────────
    @property
    def client(self) -> Any:
        """Lazy-initialize and return the Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self._url,
                    api_key=self._api_key if self._api_key else None,
                    timeout=30,
                )
                logger.info(f"Connected to Qdrant at {self._url}")
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {e}")
                raise
        return self._client

    @property
    def embedding_model(self) -> Any:
        """Lazy-initialize the embedding model."""
        if self._embedding_model is None:
            try:
                from langchain_openai import OpenAIEmbeddings

                settings = get_settings()
                self._embedding_model = OpenAIEmbeddings(
                    model=settings.embedding_model,
                    api_key=settings.openai_api_key or None,
                )
                logger.info(f"Embedding model initialized: {settings.embedding_model}")
            except Exception as e:
                logger.warning(f"OpenAI embeddings unavailable, using fallback: {e}")
                self._embedding_model = None
        return self._embedding_model

    # ── Collection Management ────────────────────────────────
    def ensure_collection(self, dimension: int | None = None) -> None:
        """Create the collection if it doesn't exist."""
        from qdrant_client.models import Distance, VectorParams

        settings = get_settings()
        dim = dimension or settings.embedding_dimension

        collections = [c.name for c in self.client.get_collections().collections]
        if self._collection_name not in collections:
            self.client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info(f"Created collection: {self._collection_name} (dim={dim})")
        else:
            logger.info(f"Collection exists: {self._collection_name}")

    def delete_collection(self) -> None:
        """Delete the collection."""
        self.client.delete_collection(self._collection_name)
        logger.info(f"Deleted collection: {self._collection_name}")

    def collection_info(self) -> dict[str, Any]:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self._collection_name)
            return {
                "name": self._collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except Exception as e:
            return {"name": self._collection_name, "error": str(e)}

    # ── Document Operations ──────────────────────────────────
    def upsert_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> int:
        """Upsert documents into the collection.

        Args:
            texts: List of text chunks.
            metadatas: List of metadata dicts (source, page, etc.).
            embeddings: Pre-computed embeddings. If None, generates them.

        Returns:
            Number of documents upserted.
        """
        from qdrant_client.models import PointStruct

        # Generate embeddings if not provided
        if embeddings is None:
            if self.embedding_model is None:
                raise ValueError("No embedding model available")
            embeddings = self.embedding_model.embed_documents(texts)

        # Create points with deterministic IDs
        points = []
        for i, (text, meta, emb) in enumerate(zip(texts, metadatas, embeddings)):
            # Deterministic ID from content hash (for idempotent upserts)
            content_hash = hashlib.md5(text.encode()).hexdigest()
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, content_hash))

            payload = {
                "content": text,
                "chunk_id": point_id,
                **meta,
            }
            points.append(PointStruct(id=point_id, vector=emb, payload=payload))

        # Batch upsert
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=self._collection_name,
                points=batch,
            )

        logger.info(f"Upserted {len(points)} documents to {self._collection_name}")
        return len(points)

    def delete_by_source(self, source: str) -> None:
        """Delete all chunks from a specific source document."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        self.client.delete(
            collection_name=self._collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source))]
            ),
        )
        logger.info(f"Deleted chunks from source: {source}")

    # ── Search Operations ────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform dense vector similarity search.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            score_threshold: Minimum similarity score.
            filters: Optional metadata filters.

        Returns:
            List of matching documents with scores.
        """
        if self.embedding_model is None:
            logger.warning("No embedding model available for search")
            return []

        # Generate query embedding
        query_embedding = self.embedding_model.embed_query(query)

        # Build filter if provided
        search_filter = None
        if filters:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            search_filter = Filter(must=conditions)

        # Search
        results = self.client.search(
            collection_name=self._collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=search_filter,
        )

        return [
            {
                "content": hit.payload.get("content", ""),
                "source": hit.payload.get("source", "Unknown"),
                "chunk_id": hit.payload.get("chunk_id", ""),
                "score": hit.score,
                "page": hit.payload.get("page", None),
                "metadata": {
                    k: v for k, v in hit.payload.items()
                    if k not in ("content", "source", "chunk_id")
                },
            }
            for hit in results
        ]

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search combining semantic vectors with keyword matching.

        In production, this combines dense vectors with sparse BM25 vectors.
        For simplicity, this implementation uses dense search with keyword boosting.
        """
        # Primary: dense vector search
        dense_results = self.search(query=query, top_k=top_k * 2, score_threshold=score_threshold)

        # Keyword boost: re-score results that contain query keywords
        query_terms = set(query.lower().split())
        for result in dense_results:
            content_lower = result["content"].lower()
            keyword_matches = sum(1 for term in query_terms if term in content_lower)
            # Boost score for keyword matches
            keyword_boost = keyword_matches * 0.05
            result["score"] = min(result["score"] + keyword_boost, 1.0)

        # Sort by boosted score and return top K
        dense_results.sort(key=lambda x: x["score"], reverse=True)
        return dense_results[:top_k]

    def get_document_info(self, source: str) -> dict[str, Any] | None:
        """Get metadata about a specific source document."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        try:
            results = self.client.scroll(
                collection_name=self._collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="source", match=MatchValue(value=source))]
                ),
                limit=1,
            )
            points, _ = results
            if points:
                payload = points[0].payload
                # Count total chunks for this source
                count_results = self.client.count(
                    collection_name=self._collection_name,
                    count_filter=Filter(
                        must=[FieldCondition(key="source", match=MatchValue(value=source))]
                    ),
                )
                return {
                    "source": source,
                    "chunk_count": count_results.count,
                    "file_type": payload.get("file_type", "Unknown"),
                    "ingested_at": payload.get("ingested_at", "Unknown"),
                }
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
        return None

    # ── Health Check ─────────────────────────────────────────
    def health_check(self) -> bool:
        """Check if the vector store is healthy and accessible."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False


def get_vector_store() -> VectorStoreService:
    """Create and return a VectorStoreService instance."""
    return VectorStoreService()
