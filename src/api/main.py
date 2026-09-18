"""
FastAPI Application — Main entry point for the API server.

Production-grade FastAPI application with:
- CORS middleware
- Structured JSON logging
- Prometheus metrics
- Lifespan events for startup/shutdown
- All route modules mounted
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Lifespan — startup and shutdown events
# ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    settings = get_settings()

    # ── Startup ──
    logger.info("🚀 Starting Enterprise Multi-Agent Platform API")
    logger.info(f"   LLM Model: {settings.llm_model}")
    logger.info(f"   Qdrant: {settings.qdrant_url}")
    logger.info(f"   MLflow: {settings.mlflow_tracking_uri}")

    # Initialize MLflow tracing
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        mlflow.langchain.autolog()
        logger.info("✅ MLflow tracing enabled")
    except Exception as e:
        logger.warning(f"⚠️ MLflow not available: {e}")

    # Store shared services in app state
    app.state.settings = settings

    yield

    # ── Shutdown ──
    logger.info("👋 Shutting down Enterprise Multi-Agent Platform API")


# ──────────────────────────────────────────────────────────────
# App Factory
# ──────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Enterprise Multi-Agent Platform",
        description=(
            "A stateful, multi-agent orchestration framework powered by LangGraph "
            "and LangChain. Routes complex business workflows across specialized "
            "sub-agents (RAG, SQL, API, Document Extraction) with citation-grounded "
            "generation and enterprise-grade observability."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request Logging Middleware ────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start_time) * 1000

        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.0f}ms)"
        )
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.0f}"
        return response

    # ── Exception Handler ────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "path": str(request.url.path),
            },
        )

    # ── Mount Routes ─────────────────────────────────────────
    from src.api.routes.chat import router as chat_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.health import router as health_router
    from src.api.routes.metrics import router as metrics_router

    app.include_router(health_router, prefix="/api/v1", tags=["Health"])
    app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
    app.include_router(documents_router, prefix="/api/v1", tags=["Documents"])
    app.include_router(metrics_router, prefix="/api/v1", tags=["Metrics"])

    # ── Root Endpoint ────────────────────────────────────────
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "Enterprise Multi-Agent Platform",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create the app instance
app = create_app()


def start_server() -> None:
    """Start the API server (entry point for CLI)."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=True,
        log_level=settings.log_level.lower(),
    )
