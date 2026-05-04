#!/usr/bin/env python3
"""
RealizeOS MCP Server — Exposes the RealizeOS venture operating system API
as native MCP tools for external agents (Claude Desktop, Hermes, etc.).

Tools:
  - realizeos_health         — Check API health and system status
  - realizeos_status         — Detailed system status with LLM/tool info
  - realizeos_list_systems   — List all configured venture systems
  - realizeos_get_system     — Get details of a specific system
  - realizeos_list_agents    — List agents for a system
  - realizeos_list_skills    — List available skills for a system
  - realizeos_chat           — Send a message to a venture agent
  - realizeos_get_history    — Get conversation history
  - realizeos_clear_history  — Clear conversation history
  - realizeos_usage          — Get LLM usage and cost statistics
  - realizeos_analytics      — Get interaction analytics
  - realizeos_suggestions    — Get pending evolution suggestions
  - realizeos_run_evolution  — Trigger a gap analysis run
  - realizeos_approve_suggestion  — Approve an evolution suggestion
  - realizeos_dismiss_suggestion  — Dismiss an evolution suggestion
  - realizeos_suggest_skill  — Generate a skill from a suggestion
  - realizeos_refine_prompt  — Suggest prompt improvements for an agent
  - realizeos_apply_refinement — Apply a prompt refinement
  - realizeos_changelog      — Get the evolution changelog
  - realizeos_reload         — Reload system configurations
  - realizeos_trigger_webhook — Trigger a skill via webhook

Transport: stdio (subprocess) or SSE (network, bearer-token protected)
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.request

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REALIZEOS_URL = os.environ.get("REALIZEOS_URL", "http://127.0.0.1:8082")
REALIZEOS_API_KEY = os.environ.get("REALIZEOS_API_KEY", "")
MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")  # Required for SSE transport

logger = logging.getLogger("realizeos-mcp")

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def _api(method: str, path: str, body: dict | None = None, timeout: int = 60) -> dict:
    """Make an authenticated HTTP request to the RealizeOS API."""
    url = f"{REALIZEOS_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if REALIZEOS_API_KEY:
        headers["X-API-Key"] = REALIZEOS_API_KEY

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        try:
            error_json = json.loads(error_body)
            detail = error_json.get("detail", error_body)
        except Exception:
            detail = error_body
        return {"error": True, "status": e.code, "detail": detail}
    except urllib.error.URLError as e:
        return {"error": True, "detail": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": True, "detail": str(e)}


def _get(path: str, timeout: int = 30) -> dict:
    return _api("GET", path, timeout=timeout)


def _post(path: str, body: dict | None = None, timeout: int = 120) -> dict:
    return _api("POST", path, body=body, timeout=timeout)


def _delete(path: str) -> dict:
    return _api("DELETE", path)


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

# Pre-parse transport, host, port from CLI before FastMCP is instantiated.
_transport = os.environ.get("MCP_TRANSPORT", "stdio")
_host = os.environ.get("MCP_HOST", "0.0.0.0")
_port = int(os.environ.get("MCP_PORT", "8090"))

for i, _arg in enumerate(sys.argv):
    if _arg == "--transport" and i + 1 < len(sys.argv):
        _transport = sys.argv[i + 1]
    elif _arg.startswith("--transport="):
        _transport = _arg.split("=", 1)[1]
    elif _arg == "--host" and i + 1 < len(sys.argv):
        _host = sys.argv[i + 1]
    elif _arg.startswith("--host="):
        _host = _arg.split("=", 1)[1]
    elif _arg == "--port" and i + 1 < len(sys.argv):
        _port = int(sys.argv[i + 1])
    elif _arg.startswith("--port="):
        _port = int(_arg.split("=", 1)[1])

if _transport in ("sse", "streamable-http"):
    mcp = FastMCP("RealizeOS", host=_host, port=_port)
else:
    mcp = FastMCP("RealizeOS")


# ---- Health & Status ----


@mcp.tool()
def realizeos_health() -> str:
    """Check RealizeOS API health, configuration status, and uptime."""
    return json.dumps(_get("/health"), indent=2)


@mcp.tool()
def realizeos_status() -> str:
    """Get detailed system status including LLM providers, tools, memory stats, and all loaded systems."""
    return json.dumps(_get("/status"), indent=2)


# ---- Systems ----


@mcp.tool()
def realizeos_list_systems() -> str:
    """List all configured venture systems with their agents and routing tables."""
    return json.dumps(_get("/api/systems"), indent=2)


@mcp.tool()
def realizeos_get_system(system_key: str) -> str:
    """Get detailed information about a specific venture system including agents, routing, brand identity, and brand voice.

    Args:
        system_key: The system identifier (e.g. 'burtucala', 'realization', 'arena', 'personal')
    """
    return json.dumps(_get(f"/api/systems/{system_key}"), indent=2)


@mcp.tool()
def realizeos_list_agents(system_key: str) -> str:
    """List all agents available in a venture system.

    Args:
        system_key: The system identifier (e.g. 'burtucala', 'realization')
    """
    return json.dumps(_get(f"/api/systems/{system_key}/agents"), indent=2)


@mcp.tool()
def realizeos_list_skills(system_key: str) -> str:
    """List available skills for a venture system, including trigger conditions and versions.

    Args:
        system_key: The system identifier
    """
    return json.dumps(_get(f"/api/systems/{system_key}/skills"), indent=2)


# ---- Chat ----


@mcp.tool()
def realizeos_chat(
    system_key: str,
    message: str,
    agent_key: str = "",
    user_id: str = "hermes-agent",
) -> str:
    """Send a message to a RealizeOS venture agent and get an AI response.

    The system routes the message to the appropriate agent based on routing rules,
    or you can specify a specific agent directly.

    Args:
        system_key: The venture system to talk to (e.g. 'burtucala', 'realization')
        message: The message to send
        agent_key: Optional specific agent to route to (e.g. 'orchestrator', 'writer', 'deal_analyst'). If empty, auto-routes.
        user_id: User identifier for session tracking (default: 'hermes-agent')
    """
    body: dict = {
        "system_key": system_key,
        "message": message,
        "user_id": user_id,
        "channel": "api",
    }
    if agent_key:
        body["agent_key"] = agent_key
    return json.dumps(_post("/api/chat", body, timeout=120), indent=2)


# ---- Conversations ----


@mcp.tool()
def realizeos_get_history(
    system_key: str,
    user_id: str = "hermes-agent",
    limit: int = 50,
) -> str:
    """Get conversation history for a user in a venture system.

    Args:
        system_key: The venture system
        user_id: The user to get history for (default: 'hermes-agent')
        limit: Maximum number of messages to return (1-500, default: 50)
    """
    return json.dumps(_get(f"/api/conversations/{system_key}/{user_id}?limit={limit}"), indent=2)


@mcp.tool()
def realizeos_clear_history(
    system_key: str,
    user_id: str = "hermes-agent",
) -> str:
    """Clear conversation history for a user in a venture system.

    Args:
        system_key: The venture system
        user_id: The user whose history to clear (default: 'hermes-agent')
    """
    return json.dumps(_delete(f"/api/conversations/{system_key}/{user_id}"), indent=2)


# ---- Sessions ----


@mcp.tool()
def realizeos_get_session(
    system_key: str,
    user_id: str = "hermes-agent",
) -> str:
    """Get the active creative session for a user, including pipeline stage, active agent, and task details.

    Args:
        system_key: The venture system
        user_id: The user to check (default: 'hermes-agent')
    """
    return json.dumps(_get(f"/api/systems/{system_key}/sessions/{user_id}"), indent=2)


# ---- Usage & Analytics ----


@mcp.tool()
def realizeos_usage(days: int = 30) -> str:
    """Get LLM usage and cost statistics across all systems.

    Args:
        days: Number of days to look back (1-365, default: 30)
    """
    return json.dumps(_get(f"/api/usage?days={days}"), indent=2)


@mcp.tool()
def realizeos_analytics(days: int = 7, system_key: str = "") -> str:
    """Get interaction analytics — call counts, token usage, and costs.

    Args:
        days: Number of days to analyze (1-365, default: 7)
        system_key: Optional system to filter by. If empty, returns analytics for all systems.
    """
    if system_key:
        return json.dumps(_get(f"/api/analytics/{system_key}?days={days}"), indent=2)
    return json.dumps(_get(f"/api/analytics?days={days}"), indent=2)


# ---- Evolution ----


@mcp.tool()
def realizeos_suggestions() -> str:
    """Get pending evolution suggestions — gaps detected in the system that could be improved."""
    return json.dumps(_get("/api/evolution/suggestions"), indent=2)


@mcp.tool()
def realizeos_run_evolution() -> str:
    """Trigger a gap analysis run to detect improvement opportunities across all systems."""
    return json.dumps(_post("/api/evolution/run"), indent=2)


@mcp.tool()
def realizeos_approve_suggestion(suggestion_id: int) -> str:
    """Approve an evolution suggestion for implementation.

    Args:
        suggestion_id: The ID of the suggestion to approve
    """
    return json.dumps(_post(f"/api/evolution/approve/{suggestion_id}"), indent=2)


@mcp.tool()
def realizeos_dismiss_suggestion(suggestion_id: int) -> str:
    """Dismiss an evolution suggestion.

    Args:
        suggestion_id: The ID of the suggestion to dismiss
    """
    return json.dumps(_post(f"/api/evolution/dismiss/{suggestion_id}"), indent=2)


@mcp.tool()
def realizeos_suggest_skill(suggestion_id: int) -> str:
    """Generate a skill YAML from a gap detection suggestion.

    Args:
        suggestion_id: The ID of the pending suggestion to generate a skill for
    """
    return json.dumps(_post(f"/api/evolution/suggest-skill/{suggestion_id}"), indent=2)


@mcp.tool()
def realizeos_refine_prompt(
    system_key: str,
    agent_key: str,
    patterns: list[str] | None = None,
) -> str:
    """Suggest prompt improvements for a venture agent based on feedback patterns.

    Args:
        system_key: The venture system
        agent_key: The agent to refine
        patterns: Optional list of feedback patterns to analyze
    """
    body = {
        "system_key": system_key,
        "agent_key": agent_key,
        "patterns": patterns or [],
    }
    return json.dumps(_post("/api/evolution/refine-prompt", body), indent=2)


@mcp.tool()
def realizeos_apply_refinement(
    system_key: str,
    agent_key: str,
    original_prompt: str,
    refined_prompt: str,
    change_summary: str,
) -> str:
    """Apply a previously suggested prompt refinement to an agent.

    Args:
        system_key: The venture system
        agent_key: The agent whose prompt to update
        original_prompt: The original prompt text
        refined_prompt: The new refined prompt text
        change_summary: Summary of what changed and why
    """
    body = {
        "system_key": system_key,
        "agent_key": agent_key,
        "original_prompt": original_prompt,
        "refined_prompt": refined_prompt,
        "change_summary": change_summary,
    }
    return json.dumps(_post("/api/evolution/apply-refinement", body), indent=2)


@mcp.tool()
def realizeos_changelog(days: int = 30) -> str:
    """Get the evolution changelog — audit trail of all system changes and improvements.

    Args:
        days: Number of days of history (1-365, default: 30)
    """
    return json.dumps(_get(f"/api/evolution/changelog?days={days}"), indent=2)


# ---- Admin ----


@mcp.tool()
def realizeos_reload() -> str:
    """Reload all system configurations from YAML. Use after updating system files."""
    return json.dumps(_post("/api/systems/reload"), indent=2)


# ---- Webhooks ----


@mcp.tool()
def realizeos_trigger_webhook(
    system_key: str,
    message: str,
    user_id: str = "hermes-webhook",
) -> str:
    """Trigger a skill in a specific venture system via webhook.

    Args:
        system_key: The venture system to trigger
        message: The message that triggers the skill
        user_id: User identifier (default: 'hermes-webhook')
    """
    body = {
        "system_key": system_key,
        "message": message,
        "user_id": user_id,
    }
    return json.dumps(_post("/webhooks/trigger-skill", body, timeout=120), indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if _transport == "stdio":
        logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
        mcp.run(transport="stdio")
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)

        if not MCP_AUTH_TOKEN:
            logger.error(
                "MCP_AUTH_TOKEN environment variable is required for network "
                "transports. Set it to a secure random string."
            )
            sys.exit(1)

        logger.info(
            f"RealizeOS MCP Server starting on {_host}:{_port} "
            f"(transport: {_transport}, auth: bearer token)"
        )

        import hmac
        import uvicorn
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Mount
        from starlette.types import ASGIApp, Receive, Scope, Send

        class BearerTokenMiddleware:
            """Reject requests without a valid Bearer token."""

            def __init__(self, app: ASGIApp, token: str) -> None:
                self.app = app
                self.token = token

            async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                if scope["type"] not in ("http", "websocket"):
                    await self.app(scope, receive, send)
                    return

                headers = dict(scope.get("headers", []))
                auth_value = headers.get(b"authorization", b"").decode()

                if not auth_value.startswith("Bearer "):
                    response = JSONResponse(
                        {"error": "Missing or invalid Authorization header. Use: Bearer <token>"},
                        status_code=401,
                        headers={"WWW-Authenticate": 'Bearer realm="RealizeOS MCP"'},
                    )
                    await response(scope, receive, send)
                    return

                provided = auth_value[7:]
                if not hmac.compare_digest(provided, self.token):
                    response = JSONResponse(
                        {"error": "Invalid bearer token"},
                        status_code=403,
                    )
                    await response(scope, receive, send)
                    return

                await self.app(scope, receive, send)

        sse_app = mcp.sse_app()
        streamable_app = mcp.streamable_http_app()

        streamable_app.routes.append(Mount("/", app=sse_app))
        streamable_app.add_middleware(BearerTokenMiddleware, token=MCP_AUTH_TOKEN)

        logger.info("Serving SSE on /sse and Streamable HTTP on /mcp")

        config = uvicorn.Config(
            streamable_app,
            host=_host,
            port=_port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        import asyncio
        asyncio.run(server.serve())
