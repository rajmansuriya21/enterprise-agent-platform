"""
Health Routes — Liveness and readiness probes.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str = "1.0.0"
    services: dict[str, str] = {}


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — checks if the API is running."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Readiness probe — checks all dependent services."""
    services: dict[str, str] = {}

    # Check Qdrant
    try:
        from src.services.vector_store import get_vector_store

        vs = get_vector_store()
        services["qdrant"] = "healthy" if vs.health_check() else "unhealthy"
    except Exception:
        services["qdrant"] = "unavailable"

    # Check Redis
    try:
        from src.services.cache import get_cache_service

        cache = get_cache_service()
        services["redis"] = "healthy" if cache.health_check() else "unhealthy"
    except Exception:
        services["redis"] = "unavailable"

    # Check Database
    try:
        from src.services.database import get_database_service

        db = get_database_service()
        services["database"] = "healthy" if db.health_check() else "unhealthy"
    except Exception:
        services["database"] = "unavailable"

    # Check MLflow
    try:
        import mlflow

        mlflow.get_tracking_uri()
        services["mlflow"] = "configured"
    except Exception:
        services["mlflow"] = "unavailable"

    # Determine overall status
    critical = ["database"]  # Only DB is critical for startup
    overall = "healthy" if all(
        services.get(s) in ("healthy", "configured")
        for s in critical
        if s in services
    ) else "degraded"

    return HealthResponse(
        status=overall,
        timestamp=datetime.utcnow().isoformat(),
        services=services,
    )
