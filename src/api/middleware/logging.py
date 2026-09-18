"""
Request Logging Middleware — Structured JSON request/response logging.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every request with correlation ID and timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        request.state.correlation_id = correlation_id

        start_time = time.time()

        # Log request
        logger.info(
            f"[{correlation_id}] → {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client": request.client.host if request.client else "unknown",
            },
        )

        # Process request
        response = await call_next(request)

        # Log response
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"[{correlation_id}] ← {response.status_code} ({elapsed_ms:.0f}ms)",
            extra={
                "correlation_id": correlation_id,
                "status_code": response.status_code,
                "latency_ms": elapsed_ms,
            },
        )

        # Add headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.0f}"

        return response
