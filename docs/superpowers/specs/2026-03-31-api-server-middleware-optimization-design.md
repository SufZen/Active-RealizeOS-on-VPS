# Design: API Server & Middleware Optimization

## Context

The RealizeOS API layer (FastAPI) is the HTTP interface exposing the engine to external clients. A security and reliability audit identified 22 issues across 6 categories: security vulnerabilities (timing attack, permissive CORS, no request limits, no security headers, error leakage), broken error handling (evolution routes returning 200 for errors, missing validation), unused rate limiting, missing observability (no request IDs or structured logging), startup reliability concerns, and Docker hardening gaps. This is the 8th optimization in the series.

**Deployment model:** Self-hosted single-tenant behind local network.
**Approach:** Surgical fix — address all 22 issues in existing file structure, no new abstractions.

---

## Section 1: Security Hardening (6 issues)

### 1a. Constant-time API key comparison
**File:** `realize_api/middleware.py:39`
**Issue:** `provided_key != self.api_key` uses Python's default string comparison which short-circuits on first mismatch — timing attack vulnerability.
**Fix:** Replace with `hmac.compare_digest(provided_key.encode(), self.api_key.encode())`.

### 1b. Remove query param API key
**File:** `realize_api/middleware.py:29`
**Issue:** `request.query_params.get("api_key", "")` leaks credentials in server logs, browser history, and referrer headers.
**Fix:** Remove query param extraction entirely. Only support `Authorization: Bearer` and `X-API-Key` headers.

### 1c. Security headers middleware
**File:** `realize_api/middleware.py` (new class)
**Issue:** No security headers on any response.
**Fix:** Add `SecurityHeadersMiddleware` that sets on every response:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 0`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

No HSTS — self-hosted may not have TLS.

### 1d. CORS production defaults
**File:** `realize_api/main.py:132`
**Issue:** `CORS_ORIGINS` defaults to `"*"` — too permissive.
**Fix:** Change default to `"http://localhost:3000,http://localhost:8080"`. Log a warning when `*` is detected.

### 1e. Request body size limit
**File:** `realize_api/middleware.py` (new class)
**Issue:** No maximum request body size — large payloads could exhaust memory.
**Fix:** Add `RequestSizeLimitMiddleware` that rejects requests with `Content-Length > MAX_REQUEST_SIZE_MB` (default 10MB, configurable via env var). Return 413 Payload Too Large.

### 1f. Sanitize error responses
**Files:** `realize_api/routes/chat.py:63`, `realize_api/routes/webhooks.py:134`
**Issue:** `str(e)[:200]` can expose internal state (file paths, stack traces).
**Fix:** Return generic `"Internal processing error"` in production. Only expose details when `REALIZE_DEBUG=true`. Log full error server-side.

---

## Section 2: Error Handling & Input Validation (4 issues)

### 2a. Fix evolution routes returning errors as HTTP 200
**File:** `realize_api/routes/evolution.py`
**Issue:** All 8 endpoints catch exceptions and return `{"error": str(e)}` with HTTP 200. Clients can't distinguish success from failure by status code.
**Fix:** Replace with `raise HTTPException(status_code=500, detail="...")` using sanitized messages. For missing resources, use 404. For invalid input, use 400.

### 2b. Fix webhook route path conflict
**File:** `realize_api/routes/webhooks.py`
**Issue:** `/webhooks/trigger-skill` (line 82) is defined AFTER `/webhooks/{endpoint_name}` (line 41). FastAPI matches `trigger-skill` as an `endpoint_name` value, so the trigger-skill handler never executes.
**Fix:** Move the `/webhooks/trigger-skill` route definition before the `/{endpoint_name}` wildcard route.

### 2c. Pydantic models for evolution endpoints
**File:** `realize_api/routes/evolution.py`
**Issue:** `refine-prompt` (line 132) and `apply-refinement` (line 186) use raw `request.json()` — no input validation, no automatic 422 for malformed requests.
**Fix:** Create Pydantic request models:
```python
class RefinePromptRequest(BaseModel):
    system_key: str
    agent_key: str
    patterns: list[str]

class RefinementChange(BaseModel):
    content: str
    location: str = "end"
    type: str = "add"  # add | modify | replace

class ApplyRefinementRequest(BaseModel):
    prompt_path: str
    changes: list[RefinementChange]
    system_key: str = ""
    agent_key: str = ""
```

### 2d. Validate query parameters
**Files:** `realize_api/routes/chat.py:82`, `realize_api/routes/evolution.py:14,26,86,174`
**Issue:** `limit` and `days` parameters have no bounds — negative values or extreme values could cause issues.
**Fix:** Use `Query(default=50, ge=1, le=500)` for `limit`, `Query(default=7, ge=1, le=365)` for `days`.

---

## Section 3: Rate Limiting Integration (2 issues)

### 3a. Wire rate limiter into API middleware
**File:** `realize_api/middleware.py` (new class)
**Issue:** `realize_core/utils/rate_limiter.py` has a complete `RateLimiter` class but it's never used by any API endpoint.
**Fix:** Add `RateLimitMiddleware` that:
- Applies only to `/api/chat` and `/webhooks/` paths (not health, status, systems)
- Uses the existing `get_rate_limiter()` singleton
- Uses API key or `"default"` as tenant ID
- Returns 429 Too Many Requests with `Retry-After` header when rate limited
- Calls `record_request()` after successful check

### 3b. Cost-based rate limiting
**File:** `realize_api/routes/chat.py`
**Issue:** `check_cost_limit()` and `record_cost()` exist but are never called.
**Fix:** After each chat response, record the estimated cost via the rate limiter. Check cost limit before processing. This piggybacks on the existing cost tracker infrastructure.

---

## Section 4: Observability (3 issues)

### 4a. Request ID middleware
**File:** `realize_api/middleware.py` (new class)
**Issue:** No way to correlate log messages with specific requests.
**Fix:** Add `RequestIDMiddleware` that:
- Generates UUID4 `X-Request-ID` for each request (or accepts from client header)
- Stores in request state for access by route handlers
- Returns in response headers
- Injects into Python logging context via `logging.Filter`

### 4b. Request logging middleware
**File:** `realize_api/middleware.py` (new class)
**Issue:** No structured request/response logging.
**Fix:** Add `RequestLoggingMiddleware` that logs per request:
- Method, path, status code, duration (ms), request ID
- Use structured format: `INFO request_id=abc method=POST path=/api/chat status=200 duration_ms=1234`
- Log at INFO for successful requests, WARNING for 4xx, ERROR for 5xx

### 4c. Rich health endpoint
**File:** `realize_api/routes/health.py`
**Issue:** `/health` returns static `{"status": "ok"}` without checking actual dependencies.
**Fix:** Enhance to check:
- Config loaded: `app.state.config` exists
- Memory DB: SQLite opens successfully
- LLM providers: API keys present (not an actual LLM call)
- System count
- Uptime (track start time in `app.state`)
```json
{
  "status": "ok",
  "checks": {
    "config": "ok",
    "memory_db": "ok",
    "llm_anthropic": "configured",
    "llm_google": "not_configured"
  },
  "systems_loaded": 8,
  "uptime_seconds": 3600
}
```

---

## Section 5: Startup & Shutdown Reliability (3 issues)

### 5a. Fix webhook channel singleton
**File:** `realize_api/routes/webhooks.py`
**Issue:** Global mutable `_webhook_channel = None` with `global` keyword — not thread-safe, inconsistent with the rest of the codebase which uses `app.state`.
**Fix:** Initialize webhook channel during lifespan and store in `app.state.webhook_channel`. Route handlers read from `request.app.state`.

### 5b. Graceful shutdown
**Files:** `Dockerfile:36`, `realize_api/main.py`
**Issue:** No graceful shutdown timeout — in-flight requests are killed immediately.
**Fix:** Add `--timeout-graceful-shutdown 30` to uvicorn command in Dockerfile. This allows 30 seconds for in-flight requests to complete before forced shutdown.

### 5c. Non-blocking KB indexing at startup
**File:** `realize_api/main.py:72-76`
**Issue:** `index_kb_files()` runs synchronously during startup. A large KB could delay health check readiness.
**Fix:** Move KB indexing to a background task (`asyncio.create_task`) so the server accepts health checks immediately. Log when indexing completes.

---

## Section 6: Docker Hardening (3 issues)

### 6a. Non-root user
**File:** `Dockerfile`
**Issue:** Container runs as root — privilege escalation risk.
**Fix:** Add after pip install:
```dockerfile
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser
```

### 6b. Resource limits
**File:** `docker-compose.yml`
**Issue:** No memory or CPU limits — runaway processes can crash the host.
**Fix:** Add deploy section:
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '2.0'
```

### 6c. Read-only root filesystem
**File:** `docker-compose.yml`
**Issue:** Container has full write access to its filesystem.
**Fix:** Add `read_only: true` with `tmpfs: [/tmp]`. Writable volumes already handle `/app/data`.

---

## Files Modified

| File | Changes |
|------|---------|
| `realize_api/middleware.py` | Constant-time comparison, remove query param auth, add SecurityHeaders/RequestSizeLimit/RateLimit/RequestID/RequestLogging middleware classes |
| `realize_api/main.py` | Register new middleware, fix CORS default, non-blocking KB indexing, track startup time |
| `realize_api/routes/chat.py` | Sanitize error messages, validate `limit` param, record cost |
| `realize_api/routes/health.py` | Rich dependency checks, uptime |
| `realize_api/routes/evolution.py` | Fix error handling (proper HTTP status codes), add Pydantic models, validate `days` params |
| `realize_api/routes/webhooks.py` | Fix route ordering, remove global singleton, sanitize errors |
| `Dockerfile` | Non-root user, graceful shutdown timeout |
| `docker-compose.yml` | Resource limits, read-only filesystem |

## Reusable Existing Code

- `realize_core/utils/rate_limiter.py:RateLimiter` — complete rate limiter, just needs middleware wrapper
- `realize_core/utils/rate_limiter.py:get_rate_limiter()` — singleton factory with config from env
- `realize_core/config.py:is_env_true()` — for `REALIZE_DEBUG` flag
- `realize_core/config.py:RATE_LIMIT_PER_MINUTE`, `COST_LIMIT_PER_HOUR_USD` — already loaded from env

## Testing Strategy

### New Tests
- `tests/test_api_middleware.py` — test all middleware classes (auth, security headers, rate limit, request size, request ID, logging)
- `tests/test_api_routes.py` — test error handling, input validation, health check dependencies

### Verification
1. `python -m pytest tests/test_api_*.py -v` — all new tests pass
2. `python -m pytest tests/ -v` — no regressions
3. `python -m ruff check realize_api/` — lint clean
4. Manual: `curl http://localhost:8080/health` returns dependency checks
5. Manual: `curl` with oversized body returns 413
6. Manual: `curl` without API key returns 401 (verify no timing difference)
7. Docker: `docker compose build && docker compose up` starts successfully as non-root

## AutoBuild Integration

This will be executed via AutoBuild's `optimize` mode:
- **Intent:** Overwrite `.autobuild/intents/active-intent.md` with optimization intent
- **Metric:** Issue resolution count (22 issues) + test pass rate
- **Build mode:** `standard` (clear scope, single approach)
- **Budget:** 5 iterations max
