"""
Dependency Injection — FastAPI dependencies for shared services.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from src.config import Settings, get_settings
from src.services.cache import CacheService, get_cache_service
from src.services.database import DatabaseService, get_database_service
from src.services.llm_provider import LLMProvider, get_llm_provider
from src.services.vector_store import VectorStoreService, get_vector_store


def get_settings_dep() -> Settings:
    """Dependency: application settings."""
    return get_settings()


def get_vector_store_dep() -> VectorStoreService:
    """Dependency: Qdrant vector store service."""
    return get_vector_store()


def get_database_dep() -> DatabaseService:
    """Dependency: SQLite database service."""
    return get_database_service()


def get_cache_dep() -> CacheService:
    """Dependency: Redis cache service."""
    return get_cache_service()


def get_llm_provider_dep() -> LLMProvider:
    """Dependency: LLM provider."""
    return get_llm_provider()
