"""
Embedding Generation — Efficient embedding pipeline with caching.

Generates embeddings using OpenAI or local models with batch processing
and caching to minimize redundant API calls.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding generation service with batch processing and caching."""

    def __init__(self, cache_service: Any | None = None) -> None:
        self._cache = cache_service
        self._model: Any | None = None
        self._total_embedded: int = 0

    @property
    def model(self) -> Any:
        """Lazy-initialize the embedding model."""
        if self._model is None:
            try:
                from langchain_openai import OpenAIEmbeddings

                settings = get_settings()
                self._model = OpenAIEmbeddings(
                    model=settings.embedding_model,
                    api_key=settings.openai_api_key or None,
                )
                logger.info(f"Embedding model initialized: {settings.embedding_model}")
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                raise
        return self._model

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = 100,
        use_cache: bool = True,
    ) -> list[list[float]]:
        """Embed a list of texts with batch processing and optional caching.

        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts per embedding API call.
            use_cache: Whether to use cache for embeddings.

        Returns:
            List of embedding vectors.
        """
        embeddings: list[list[float]] = [[] for _ in texts]
        texts_to_embed: list[tuple[int, str]] = []

        # Check cache first
        if use_cache and self._cache:
            for i, text in enumerate(texts):
                cached = self._cache.get_cached_embedding(text)
                if cached:
                    embeddings[i] = cached
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))

        cache_hits = len(texts) - len(texts_to_embed)
        if cache_hits > 0:
            logger.info(f"Embedding cache hits: {cache_hits}/{len(texts)}")

        # Batch embed uncached texts
        if texts_to_embed:
            for batch_start in range(0, len(texts_to_embed), batch_size):
                batch = texts_to_embed[batch_start : batch_start + batch_size]
                batch_texts = [t for _, t in batch]

                try:
                    batch_embeddings = self.model.embed_documents(batch_texts)

                    for (orig_idx, text), emb in zip(batch, batch_embeddings):
                        embeddings[orig_idx] = emb
                        # Cache the embedding
                        if use_cache and self._cache:
                            self._cache.cache_embedding(text, emb)

                    self._total_embedded += len(batch)
                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    raise

        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query text."""
        return self.model.embed_query(query)

    @property
    def stats(self) -> dict[str, int]:
        return {"total_embedded": self._total_embedded}


def get_embedding_service(cache_service: Any | None = None) -> EmbeddingService:
    """Create and return an EmbeddingService instance."""
    return EmbeddingService(cache_service=cache_service)
