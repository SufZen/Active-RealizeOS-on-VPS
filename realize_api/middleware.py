"""
API Middleware: Authentication, security headers, rate limiting, observability.
"""

import hmac
import logging
import os
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware with constant-time comparison."""

    # Paths that skip authentication
    _PUBLIC_PATHS = frozenset(("/health", "/status", "/docs", "/openapi.json", "/redoc"))

    def __init__(self, app, api_key: str):
        super().__init__(app)
        self._api_key_bytes = api_key.encode()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._PUBLIC_PATHS:
            return await call_next(request)

        # Extract key from headers only (query param removed for security)
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")

        provided_key = ""
        if auth_header.startswith("Bearer "):
            provided_key = auth_header[7:]
        elif api_key_header:
            provided_key = api_key_header

        # Constant-time comparison to prevent timing attacks
        if not provided_key or not hmac.compare_digest(
            provided_key.encode(), self._api_key_bytes
        ):
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"},
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


# ---------------------------------------------------------------------------
# Request Size Limit
# ---------------------------------------------------------------------------


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests exceeding the configured body size limit."""

    def __init__(self, app, max_size_bytes: int | None = None):
        super().__init__(app)
        max_mb = float(os.environ.get("MAX_REQUEST_SIZE_MB", "10"))
        self.max_size = max_size_bytes or int(max_mb * 1024 * 1024)

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request body too large",
                    "max_bytes": self.max_size,
                },
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces per-tenant rate limiting on chat and webhook endpoints."""

    _RATE_LIMITED_PREFIXES = ("/api/chat", "/webhooks/")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not any(path.startswith(p) for p in self._RATE_LIMITED_PREFIXES):
            return await call_next(request)

        from realize_core.utils.rate_limiter import get_rate_limiter

        limiter = get_rate_limiter()
        tenant_id = request.headers.get("X-API-Key", "default")

        if not limiter.check_rate_limit(tenant_id):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        if not limiter.check_cost_limit(tenant_id):
            return JSONResponse(
                status_code=429,
                content={"error": "Hourly cost limit exceeded"},
                headers={"Retry-After": "300"},
            )

        limiter.record_request(tenant_id)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generates or propagates a unique request ID for every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Request Logging
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status, duration, and request ID for every request."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        request_id = getattr(request.state, "request_id", "-")
        msg = (
            f"request_id={request_id} method={request.method} "
            f"path={request.url.path} status={response.status_code} "
            f"duration_ms={duration_ms:.1f}"
        )

        if response.status_code >= 500:
            logger.error(msg)
        elif response.status_code >= 400:
            logger.warning(msg)
        else:
            logger.info(msg)

        return response
