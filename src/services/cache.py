"""
Redis Cache Service — Session management and query caching.

Provides TTL-based caching for LLM responses and embeddings,
with graceful fallback when Redis is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-backed cache with graceful fallback to in-memory cache."""

    def __init__(self, redis_url: str | None = None) -> None:
        settings = get_settings()
        self._redis_url = redis_url or settings.redis_url
        self._ttl = settings.redis_ttl_seconds
        self._client: Any | None = None
        self._connected = False

        # In-memory fallback cache
        self._memory_cache: dict[str, Any] = {}
        self._max_memory_items = 1000

    @property
    def client(self) -> Any | None:
        """Lazy-initialize Redis client with graceful fallback."""
        if self._client is None and not self._connected:
            try:
                import redis

                self._client = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                # Test connection
                self._client.ping()
                self._connected = True
                logger.info(f"Connected to Redis at {self._redis_url}")
            except Exception as e:
                logger.warning(
                    f"Redis unavailable ({e}), using in-memory fallback cache"
                )
                self._client = None
                self._connected = False
        return self._client

    # ── Cache Key Generation ─────────────────────────────────
    @staticmethod
    def _make_key(prefix: str, *parts: str) -> str:
        """Generate a cache key from prefix and parts."""
        content = ":".join(parts)
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{prefix}:{content_hash}"

    # ── Core Operations ──────────────────────────────────────
    def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        if self.client:
            try:
                value = self.client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")

        # Fallback to memory cache
        return self._memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in cache with TTL."""
        ttl = ttl or self._ttl
        serialized = json.dumps(value, default=str)

        if self.client:
            try:
                self.client.setex(key, ttl, serialized)
                return
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")

        # Fallback to memory cache (no TTL in memory)
        if len(self._memory_cache) >= self._max_memory_items:
            # Evict oldest entries (simple FIFO)
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
        self._memory_cache[key] = value

    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        if self.client:
            try:
                self.client.delete(key)
            except Exception:
                pass
        self._memory_cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        if self.client:
            try:
                self.client.flushdb()
            except Exception:
                pass
        self._memory_cache.clear()

    # ── Specialized Cache Methods ────────────────────────────
    def cache_llm_response(self, query: str, response: str, model: str = "") -> None:
        """Cache an LLM response for a specific query."""
        key = self._make_key("llm", model, query)
        self.set(key, {"response": response, "model": model})

    def get_cached_llm_response(self, query: str, model: str = "") -> str | None:
        """Get a cached LLM response for a query."""
        key = self._make_key("llm", model, query)
        cached = self.get(key)
        return cached["response"] if cached else None

    def cache_embedding(self, text: str, embedding: list[float]) -> None:
        """Cache an embedding vector for a text."""
        key = self._make_key("emb", text)
        self.set(key, embedding, ttl=86400)  # 24h TTL for embeddings

    def get_cached_embedding(self, text: str) -> list[float] | None:
        """Get a cached embedding for text."""
        key = self._make_key("emb", text)
        return self.get(key)

    def cache_session(self, session_id: str, data: dict) -> None:
        """Cache session data."""
        key = f"session:{session_id}"
        self.set(key, data, ttl=3600)  # 1h session TTL

    def get_session(self, session_id: str) -> dict | None:
        """Get cached session data."""
        key = f"session:{session_id}"
        return self.get(key)

    # ── Health Check ─────────────────────────────────────────
    def health_check(self) -> bool:
        """Check if the cache service is healthy."""
        if self.client:
            try:
                return self.client.ping()
            except Exception:
                return False
        # Memory cache is always "healthy"
        return True

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = {"backend": "redis" if self._connected else "memory"}
        if self.client and self._connected:
            try:
                info = self.client.info("memory")
                stats["used_memory"] = info.get("used_memory_human", "N/A")
                stats["keys"] = self.client.dbsize()
            except Exception:
                pass
        else:
            stats["keys"] = len(self._memory_cache)
            stats["max_keys"] = self._max_memory_items
        return stats


def get_cache_service() -> CacheService:
    """Create and return a CacheService instance."""
    return CacheService()
