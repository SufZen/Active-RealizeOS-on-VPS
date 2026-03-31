"""
Health and status endpoints.
"""

import logging
import os
import time

from fastapi import APIRouter, Request

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health(request: Request):
    """Health check with dependency status."""
    checks = {}

    # Config loaded
    checks["config"] = "ok" if getattr(request.app.state, "config", None) else "missing"

    # Memory DB accessible
    try:
        from realize_core.memory.store import db_connection

        with db_connection() as conn:
            conn.execute("SELECT 1")
        checks["memory_db"] = "ok"
    except Exception:
        checks["memory_db"] = "unavailable"

    # LLM provider keys
    if os.environ.get("ANTHROPIC_API_KEY"):
        checks["llm_anthropic"] = "configured"
    else:
        checks["llm_anthropic"] = "not_configured"

    if os.environ.get("GOOGLE_AI_API_KEY"):
        checks["llm_google"] = "configured"
    else:
        checks["llm_google"] = "not_configured"

    # Overall status: degraded if any critical check fails
    overall = "ok"
    if checks.get("config") != "ok":
        overall = "degraded"
    if checks.get("memory_db") != "ok":
        overall = "degraded"

    # Uptime
    startup_time = getattr(request.app.state, "startup_time", None)
    uptime_seconds = int(time.time() - startup_time) if startup_time else 0

    systems = getattr(request.app.state, "systems", {})

    return {
        "status": overall,
        "service": "realize-os",
        "checks": checks,
        "systems_loaded": len(systems),
        "uptime_seconds": uptime_seconds,
    }


@router.get("/status")
async def status(request: Request):
    """Detailed system status."""
    from realize_core.config import is_env_true

    systems = request.app.state.systems

    # Check LLM availability
    llm_status = {}
    if os.environ.get("ANTHROPIC_API_KEY"):
        llm_status["anthropic"] = "configured"
    if os.environ.get("GOOGLE_AI_API_KEY"):
        llm_status["google"] = "configured"

    # Check tool availability
    tools_status = {}
    if os.environ.get("BRAVE_API_KEY"):
        tools_status["web_search"] = "configured"
    if is_env_true("BROWSER_ENABLED", default=False):
        tools_status["browser"] = "enabled"

    try:
        from realize_core.tools.google_auth import get_credentials

        if get_credentials():
            tools_status["google_workspace"] = "authenticated"
        else:
            tools_status["google_workspace"] = "not configured"
    except Exception:
        tools_status["google_workspace"] = "not available"

    # MCP status
    if is_env_true("MCP_ENABLED", default=False):
        try:
            from realize_core.tools.mcp import get_mcp_hub

            hub = get_mcp_hub()
            if hub.servers:
                connected = sum(1 for s in hub.servers.values() if s.connected)
                tools_status["mcp"] = f"{connected}/{len(hub.servers)} servers"
            else:
                tools_status["mcp"] = "enabled"
        except Exception:
            tools_status["mcp"] = "enabled"

    # Memory stats
    memory_status = {}
    try:
        from realize_core.utils.cost_tracker import get_usage_summary

        memory_status["llm_usage"] = get_usage_summary()
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "0.1.0",
        "systems": {
            k: {"name": v.get("name", k), "agents": list(v.get("agents", {}).keys())} for k, v in systems.items()
        },
        "llm": llm_status,
        "tools": tools_status,
        "memory": memory_status,
    }
