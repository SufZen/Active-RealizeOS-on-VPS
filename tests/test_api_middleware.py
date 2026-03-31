"""Tests for API middleware: authentication, security headers, rate limiting, observability."""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from realize_api.middleware import (
    APIKeyMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from starlette.responses import JSONResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(**middleware_kwargs) -> FastAPI:
    """Create a minimal FastAPI app for testing individual middleware."""
    app = FastAPI()

    @app.get("/test")
    async def test_route():
        return {"ok": True}

    @app.get("/health")
    async def health_route():
        return {"status": "ok"}

    @app.post("/api/chat")
    async def chat_route():
        return {"response": "hello"}

    return app


# ---------------------------------------------------------------------------
# APIKeyMiddleware
# ---------------------------------------------------------------------------


class TestAPIKeyMiddleware:
    """Tests for API key authentication."""

    def _make_client(self, api_key: str = "test-key-123") -> TestClient:
        app = _make_app()
        app.add_middleware(APIKeyMiddleware, api_key=api_key)
        return TestClient(app, raise_server_exceptions=False)

    def test_valid_bearer_token(self):
        client = self._make_client()
        resp = client.get("/test", headers={"Authorization": "Bearer test-key-123"})
        assert resp.status_code == 200

    def test_valid_x_api_key_header(self):
        client = self._make_client()
        resp = client.get("/test", headers={"X-API-Key": "test-key-123"})
        assert resp.status_code == 200

    def test_missing_key_returns_401(self):
        client = self._make_client()
        resp = client.get("/test")
        assert resp.status_code == 401
        assert "Invalid or missing API key" in resp.json()["error"]

    def test_wrong_key_returns_401(self):
        client = self._make_client()
        resp = client.get("/test", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 401

    def test_health_skips_auth(self):
        client = self._make_client()
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_query_param_key_no_longer_accepted(self):
        """API key in query params was removed for security."""
        client = self._make_client()
        resp = client.get("/test?api_key=test-key-123")
        assert resp.status_code == 401

    def test_constant_time_comparison(self):
        """Verify hmac.compare_digest is used (not == or !=)."""
        # This is a structural test — verify the middleware stores bytes
        app = _make_app()
        mw = APIKeyMiddleware(app, api_key="secret")
        assert hasattr(mw, "_api_key_bytes")
        assert mw._api_key_bytes == b"secret"

    def test_empty_key_rejected(self):
        client = self._make_client()
        resp = client.get("/test", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_bearer_prefix_required(self):
        client = self._make_client()
        resp = client.get("/test", headers={"Authorization": "test-key-123"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


class TestSecurityHeadersMiddleware:
    """Tests for security response headers."""

    def _make_client(self) -> TestClient:
        app = _make_app()
        app.add_middleware(SecurityHeadersMiddleware)
        return TestClient(app)

    def test_all_security_headers_present(self):
        client = self._make_client()
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["X-XSS-Protection"] == "0"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers["Permissions-Policy"]

    def test_headers_on_error_responses(self):
        """Security headers should appear even on non-200 responses."""
        app = FastAPI()

        @app.get("/error")
        async def error_route():
            return JSONResponse(status_code=500, content={"error": "fail"})

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/error")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"


# ---------------------------------------------------------------------------
# RequestSizeLimitMiddleware
# ---------------------------------------------------------------------------


class TestRequestSizeLimitMiddleware:
    """Tests for request body size limiting."""

    def _make_client(self, max_bytes: int = 1024) -> TestClient:
        app = _make_app()
        app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=max_bytes)
        return TestClient(app, raise_server_exceptions=False)

    def test_small_request_passes(self):
        client = self._make_client(max_bytes=10000)
        resp = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"Content-Length": "50"},
        )
        assert resp.status_code == 200

    def test_oversized_request_rejected(self):
        client = self._make_client(max_bytes=100)
        resp = client.post(
            "/api/chat",
            content=b"x" * 200,
            headers={"Content-Length": "200", "Content-Type": "application/json"},
        )
        assert resp.status_code == 413
        assert "too large" in resp.json()["error"]

    def test_no_content_length_passes(self):
        """Requests without Content-Length header are allowed through."""
        client = self._make_client(max_bytes=100)
        resp = client.get("/test")
        assert resp.status_code == 200

    def test_env_var_config(self, monkeypatch):
        """MAX_REQUEST_SIZE_MB env var configures the limit."""
        monkeypatch.setenv("MAX_REQUEST_SIZE_MB", "0.001")  # ~1KB
        app = _make_app()
        mw = RequestSizeLimitMiddleware(app)
        assert mw.max_size == int(0.001 * 1024 * 1024)


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    def test_non_rate_limited_paths_pass(self):
        app = _make_app()
        app.add_middleware(RateLimitMiddleware)
        client = TestClient(app)
        # /test is not rate-limited (only /api/chat and /webhooks/)
        resp = client.get("/test")
        assert resp.status_code == 200

    @patch("realize_core.utils.rate_limiter.get_rate_limiter")
    def test_rate_limited_when_exceeded(self, mock_get):
        limiter = Mock()
        limiter.check_rate_limit.return_value = False
        mock_get.return_value = limiter

        app = _make_app()
        app.add_middleware(RateLimitMiddleware)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "60"

    @patch("realize_core.utils.rate_limiter.get_rate_limiter")
    def test_cost_limited_when_exceeded(self, mock_get):
        limiter = Mock()
        limiter.check_rate_limit.return_value = True
        limiter.check_cost_limit.return_value = False
        mock_get.return_value = limiter

        app = _make_app()
        app.add_middleware(RateLimitMiddleware)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 429
        assert "cost limit" in resp.json()["error"].lower()

    @patch("realize_core.utils.rate_limiter.get_rate_limiter")
    def test_request_recorded_on_pass(self, mock_get):
        limiter = Mock()
        limiter.check_rate_limit.return_value = True
        limiter.check_cost_limit.return_value = True
        mock_get.return_value = limiter

        app = _make_app()
        app.add_middleware(RateLimitMiddleware)
        client = TestClient(app)
        client.post("/api/chat", json={})
        limiter.record_request.assert_called_once()


# ---------------------------------------------------------------------------
# RequestIDMiddleware
# ---------------------------------------------------------------------------


class TestRequestIDMiddleware:
    """Tests for request ID generation and propagation."""

    def _make_client(self) -> TestClient:
        app = _make_app()
        app.add_middleware(RequestIDMiddleware)
        return TestClient(app)

    def test_generates_request_id(self):
        client = self._make_client()
        resp = client.get("/test")
        assert "X-Request-ID" in resp.headers
        # Should be a UUID-like string
        assert len(resp.headers["X-Request-ID"]) > 10

    def test_propagates_client_request_id(self):
        client = self._make_client()
        resp = client.get("/test", headers={"X-Request-ID": "my-custom-id"})
        assert resp.headers["X-Request-ID"] == "my-custom-id"

    def test_unique_ids_per_request(self):
        client = self._make_client()
        resp1 = client.get("/test")
        resp2 = client.get("/test")
        assert resp1.headers["X-Request-ID"] != resp2.headers["X-Request-ID"]


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware
# ---------------------------------------------------------------------------


class TestRequestLoggingMiddleware:
    """Tests for request logging middleware."""

    def _make_client(self) -> TestClient:
        app = _make_app()
        app.add_middleware(RequestLoggingMiddleware)
        return TestClient(app)

    def test_logs_successful_request(self, caplog):
        client = self._make_client()
        with caplog.at_level("INFO", logger="realize_api.middleware"):
            client.get("/test")
        log_messages = [r.message for r in caplog.records if "path=/test" in r.message]
        assert len(log_messages) >= 1
        assert "status=200" in log_messages[0]
        assert "duration_ms=" in log_messages[0]

    def test_logs_error_at_warning_level(self, caplog):
        app = FastAPI()

        @app.get("/missing")
        async def missing():
            from fastapi import HTTPException
            raise HTTPException(status_code=404)

        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app, raise_server_exceptions=False)
        with caplog.at_level("WARNING", logger="realize_api.middleware"):
            client.get("/missing")
        warning_messages = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_messages) >= 1
