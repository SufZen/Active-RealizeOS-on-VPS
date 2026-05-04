> **Internal/historical document — not user-facing operator documentation. See root `CLAUDE.md` and `setup-guide.md` for current operating guidance.**

# Tools & External Integrations Optimization — Design Spec

## Context

The Tools system (`realize_core/tools/`) is RealizeOS's interface to external services — Google Workspace, web search/scraping, browser automation, MCP servers, KB storage, and voice/phone. A code review identified 14 issues across security (SSRF, path traversal), reliability (missing timeouts, OAuth race conditions, zombie processes), robustness (no rate limiting, no result size limits), code quality (dead code, missing registrations), and observability (no health checks, no timing).

This optimization addresses all 14 issues in a bottom-up pass (tool by tool), ordered for dependency management. It follows the same tiered approach that succeeded for the Skills System optimization.

## Issue Inventory

| # | Issue | Tier | Files |
|---|-------|------|-------|
| 1 | SSRF: No URL validation for user-supplied URLs | P0 | web.py, browser.py |
| 2 | KB path traversal bypass (string check, not resolved path) | P0 | kb_tools.py |
| 3 | No per-tool timeout on Google API calls | P1 | google_workspace.py |
| 4 | OAuth token expires between check and API call | P1 | google_auth.py |
| 5 | MCP `call_tool()` has no timeout | P1 | mcp.py |
| 6 | Browser `navigate` silently swallows all errors | P1 | browser.py |
| 7 | Browser sessions have no TTL / max-age cleanup | P1 | browser.py |
| 8 | No rate limiting / backoff on external APIs | P2 | web.py, google_workspace.py, voice_tools.py |
| 9 | No result size limit at registry level | P2 | tool_registry.py |
| 10 | Dead `WEB_TOOL_SCHEMAS` in web.py (unused duplicate) | P3 | web.py |
| 11 | Voice + KB tools not in auto-discovery | P3 | tool_registry.py |
| 12 | Schema descriptions could be richer for LLM selection | P3 | all *_tool.py |
| 13 | No tool health check at startup | P4 | tool_registry.py |
| 14 | No execution timing in ToolResult metadata | P4 | tool_registry.py |

## Architecture: Bottom-Up Implementation

Each tool is fixed independently, ordered so dependencies are resolved before dependents.

### Pass 1: `kb_tools.py` — P0 Path Traversal Fix

**Problem:** `str(clean_path).startswith("systems/")` can be bypassed with paths like `systems/../../etc/passwd` because the check runs before path resolution.

**Fix:** After the existing checks, resolve the full path and verify containment:
```python
resolved = full_path.resolve()
base_resolved = base.resolve()
if not str(resolved).startswith(str(base_resolved)):
    return {"status": "error", "error": "Path escapes KB directory"}
```

### Pass 2: `web.py` + `web_tool.py` — P0 SSRF + P2 Retry + P3 Cleanup

**P0 — URL Validation:**
Add `_validate_url(url: str) -> str | None` that returns an error message if the URL is unsafe, `None` if ok:
- Block schemes other than `http`/`https`
- Resolve hostname to IP, block private/reserved ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16, ::1, fc00::/7)
- Block `localhost` and common internal hostnames
- Apply in both `web_search` (query is safe, but `web_fetch` is the risk) and `web_fetch`

**P2 — Retry with backoff:**
Add retry logic for `web_search` on 429/503 responses (max 3 attempts, exponential backoff starting at 1s).

**P3 — Dead code removal:**
Remove `WEB_TOOL_SCHEMAS`, `TOOL_FUNCTIONS`, `WEB_READ_TOOLS`, `WEB_WRITE_TOOLS` from `web.py` — they are unused. The `web_tool.py` wrapper defines its own schemas and imports functions directly.

### Pass 3: `browser.py` + `browser_tool.py` — P0 SSRF + P1 Error Handling + P1 Session TTL

**P0 — URL Validation:**
Import and apply `_validate_url` from `web.py` in `browser_navigate`. Return a `ToolResult.fail` if the URL is blocked.

**P1 — Error handling in `browser_navigate`:**
The current code has `except Exception: pass` after `goto()`. Fix: catch the exception, log it, and include it in the return dict so the LLM knows what happened (e.g., `"navigation_error": str(e)[:200]`). Still continue to extract whatever content loaded.

**P1 — Session TTL:**
Add `created_at: float` to `BrowserSession`. In `_get_session()`, check if the session is older than `BROWSER_SESSION_TTL` (default 30 min). If so, close it and create a new one. Also add `cleanup_stale_sessions()` callable from the registry health check.

### Pass 4: `google_auth.py` — P1 Proactive Token Refresh

**Problem:** Token is only refreshed when `_credentials.expired` is True. If the token expires between this check and the actual Google API call (seconds later), the call fails.

**Fix:** Refresh if the token expires within a 5-minute window:
```python
from datetime import timedelta
if _credentials.expired or (
    _credentials.expiry and _credentials.expiry - datetime.now(UTC) < timedelta(minutes=5)
):
    _credentials.refresh(Request())
    _save_tokens(...)
```

### Pass 5: `google_workspace.py` + `google_workspace_tool.py` — P1 Timeouts + P2 Retry

**P1 — Timeouts:**
Each `asyncio.to_thread()` call runs Google API operations that can hang. Wrap with `asyncio.wait_for(asyncio.to_thread(...), timeout=30)` for read operations and `timeout=45` for write operations.

**P2 — Retry with backoff:**
Add retry logic for Google API 429/503/500 errors in the sync helper functions (max 3 attempts, exponential backoff). Use `googleapiclient.errors.HttpError` to catch and inspect status codes.

### Pass 6: `mcp.py` — P1 Call Timeout

**Problem:** `call_tool()` awaits `self.session.call_tool()` with no timeout. A hung MCP server blocks the entire request.

**Fix:**
```python
result = await asyncio.wait_for(
    self.session.call_tool(tool_name, arguments=arguments),
    timeout=self._call_timeout  # default 60s, configurable per-server
)
```
Add `call_timeout: int = 60` to `MCPServerConnection.__init__` and load from YAML config.

### Pass 7: `voice_tools.py` — P2 Retry

Add retry with backoff for `initiate_outbound_call` on 429/503/500 responses from ElevenLabs API (max 2 retries, 2s initial backoff). The `get_call_status` is a simple poll — no retry needed.

### Pass 8: `tool_registry.py` — P2 Truncation + P3 Discovery + P4 Health/Timing

**P2 — Result size limit:**
In `execute()`, after getting the result, truncate `result.output` if it exceeds `MAX_RESULT_CHARS` (default 12000):
```python
if result.output and len(result.output) > MAX_RESULT_CHARS:
    result.output = result.output[:MAX_RESULT_CHARS] + "\n\n[...truncated]"
    result.metadata["truncated"] = True
```

**P3 — Auto-discovery additions:**
Add to `known_modules`:
```python
"realize_core.tools.kb_tool",     # new file: BaseTool wrapper for kb_tools.py
"realize_core.tools.voice_tool",  # new file: BaseTool wrapper for voice_tools.py
```
Create two new thin wrapper files following the existing pattern (e.g., `google_workspace_tool.py`):
- `kb_tool.py`: `KBTool(BaseTool)` wrapping `kb_append`, category=DATA, `is_available()` always True
- `voice_tool.py`: `VoiceTool(BaseTool)` wrapping `initiate_outbound_call`/`get_call_status`, category=COMMUNICATION, `is_available()` checks ElevenLabs config

**P4 — Health check:**
```python
def check_health(self) -> dict[str, bool]:
    return {name: tool.is_available() for name, tool in self._tools.items()}
```

**P4 — Execution timing:**
Wrap the `execute()` call with timing:
```python
import time
start = time.monotonic()
result = await tool.execute(action_name, params)
result.metadata["duration_ms"] = round((time.monotonic() - start) * 1000)
```

### Pass 9: Schema Enrichment — P3

Improve schema descriptions across all `*_tool.py` files:
- Add "Use this when..." phrasing to help LLMs select tools
- Specify parameter formats explicitly (e.g., "ISO 8601 datetime string", "E.164 phone number")
- Add examples in parameter descriptions where helpful
- Ensure `description` fields on optional parameters explain defaults

### Pass 10: Tests

New tests to add to `tests/test_tool_sdk.py` (or a new `tests/test_tool_security.py`):

- **URL validation:** Test SSRF blocklist (private IPs, localhost, non-http schemes, valid URLs)
- **KB path traversal:** Test that `../` paths and resolved-outside-base paths are rejected
- **Result truncation:** Test that oversized results get truncated with metadata flag
- **Execution timing:** Test that `duration_ms` appears in result metadata
- **Session TTL:** Test that expired sessions get replaced
- **Registry health check:** Test that health check returns correct availability status

## Scope

### IN
- `realize_core/tools/base_tool.py` — no changes expected
- `realize_core/tools/tool_registry.py` — truncation, discovery, health check, timing
- `realize_core/tools/web.py` — URL validation, retry, dead code removal
- `realize_core/tools/web_tool.py` — SSRF validation call
- `realize_core/tools/browser.py` — URL validation, error handling, session TTL
- `realize_core/tools/browser_tool.py` — minimal changes
- `realize_core/tools/google_auth.py` — proactive token refresh
- `realize_core/tools/google_workspace.py` — timeouts, retry
- `realize_core/tools/google_workspace_tool.py` — minimal changes
- `realize_core/tools/mcp.py` — call timeout
- `realize_core/tools/kb_tools.py` — path traversal fix
- `realize_core/tools/voice_tools.py` — retry
- `tests/test_tool_sdk.py` — extended tests
- New: `tests/test_tool_security.py` — security-focused tests

### OUT
- `realize_core/llm/` — LLM routing unchanged
- `realize_core/skills/` — Skills system unchanged
- `realize_core/channels/` — Channel adapters unchanged
- `realize_api/` — API layer unchanged
- `realize_core/base_handler.py` — Message flow unchanged

## Verification

After implementation:
1. `python -m pytest tests/test_tool_sdk.py tests/test_tool_security.py -v` — all pass
2. `python -m pytest tests/ -v` — full suite, no regressions
3. `python -m ruff check realize_core/tools/` — lint clean
4. `python -m ruff format --check realize_core/tools/` — format clean
5. Manual: verify URL validation blocks `http://127.0.0.1`, `http://169.254.169.254`, `file:///etc/passwd`
6. Manual: verify KB append rejects `systems/../../etc/passwd`
