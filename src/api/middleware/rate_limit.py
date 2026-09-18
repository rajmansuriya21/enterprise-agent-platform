"""
Rate Limiting Middleware — Token bucket rate limiter.
"""

from __future__ import annotations

import time
import logging
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config import get_settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple token bucket rate limiter per client IP."""

    def __init__(self, app, rpm: int | None = None) -> None:
        super().__init__(app)
        settings = get_settings()
        self._rpm = rpm or settings.rate_limit_rpm
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": self._rpm, "last_refill": time.time()}
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if a request is within rate limits. Returns True if allowed."""
        bucket = self._buckets[client_ip]
        now = time.time()

        # Refill tokens based on elapsed time
        elapsed = now - bucket["last_refill"]
        tokens_to_add = elapsed * (self._rpm / 60.0)
        bucket["tokens"] = min(self._rpm, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/api/v1/health", "/api/v1/ready", "/docs", "/redoc"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self._rpm} requests per minute",
                    "retry_after_seconds": 60,
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
