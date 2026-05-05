"""
RealizeOS API Server — FastAPI application.

Provides REST endpoints for chat, system management, and health checks.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from realize_api.middleware import (
    APIKeyMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from realize_api.routes import chat, evolution, health, kb, systems, webhooks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    # Startup
    logger.info("RealizeOS API starting up...")
    app.state.startup_time = time.time()

    from realize_core.config import KB_PATH, build_systems_dict, get_features, is_env_true, load_config

    config = load_config()
    kb_path = Path(config.get("kb_path", KB_PATH)).resolve()
    app.state.config = config
    app.state.kb_path = kb_path
    app.state.features = get_features(config)
    app.state.systems = build_systems_dict(config, kb_path=kb_path)
    app.state.shared_config = config.get(
        "shared",
        {
            "identity": "shared/identity.md",
            "preferences": "shared/user-preferences.md",
        },
    )

    # Initialize LLM routing config from YAML
    try:
        from realize_core.llm.router import load_routing_config

        load_routing_config(config)
    except Exception as e:
        logger.debug(f"LLM routing config loading skipped: {e}")

    # Initialize memory store
    from realize_core.memory.store import init_db

    init_db()

    # Initialize analytics tables (for evolution tracking)
    try:
        from realize_core.evolution.analytics import init_analytics_tables

        init_analytics_tables()
    except Exception as e:
        logger.debug(f"Analytics tables init skipped: {e}")

    # Load skills from the current KB so API surfaces can list them immediately.
    try:
        from realize_core.skills.detector import reload_skills

        reload_skills(kb_path=kb_path)
    except Exception as e:
        logger.debug(f"Skill loading skipped: {e}")

    # Initialize KB index in the background (non-blocking)
    async def _index_kb():
        try:
            from realize_core.kb.indexer import index_kb_files

            index_kb_files(str(kb_path))
            logger.info("KB index initialized")
        except Exception as e:
            logger.warning(f"KB indexing skipped: {e}")

    asyncio.create_task(_index_kb())

    # Warm prompt cache
    try:
        from realize_core.prompt.builder import warm_cache

        warm_cache(kb_path, app.state.systems, app.state.shared_config)
    except Exception as e:
        logger.debug(f"Cache warming skipped: {e}")

    # Initialize webhook channel and store in app.state
    try:
        from realize_core.channels.webhooks import WebhookChannel

        webhook_channel = WebhookChannel()
        config_paths = [Path("realize-os.yaml"), Path("../realize-os.yaml")]
        for path in config_paths:
            if path.exists():
                webhook_channel.load_from_yaml(path)
                logger.info(f"Loaded webhook endpoints from {path} ({webhook_channel.endpoint_count} endpoints)")
                break
        app.state.webhook_channel = webhook_channel
    except Exception as e:
        logger.debug(f"Webhook channel init skipped: {e}")
        app.state.webhook_channel = None

    # Initialize MCP if enabled
    if is_env_true("MCP_ENABLED", default=False):
        try:
            from realize_core.tools.mcp import initialize_mcp

            await initialize_mcp()
        except Exception as e:
            logger.warning(f"MCP initialization skipped: {e}")

    logger.info(f"RealizeOS API ready — {len(app.state.systems)} system(s) loaded")
    yield

    # Shutdown
    logger.info("RealizeOS API shutting down...")
    try:
        from realize_core.tools.web import close_http_client

        await close_http_client()
    except Exception:
        pass
    try:
        from realize_core.tools.browser import cleanup_all_sessions

        await cleanup_all_sessions()
    except Exception:
        pass
    try:
        from realize_core.tools.mcp import shutdown_mcp

        await shutdown_mcp()
    except Exception:
        pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    import os

    app = FastAPI(
        title="RealizeOS",
        description="AI Operations System — Multi-agent, multi-venture, self-evolving.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- Middleware stack (outermost → innermost) ---
    # Note: FastAPI middleware is applied in reverse registration order,
    # so the LAST added middleware runs FIRST on requests.

    # CORS
    allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    if "*" in allowed_origins:
        logger.warning(
            "CORS_ORIGINS contains '*' — this is insecure for production. "
            "Set explicit origins via the CORS_ORIGINS environment variable."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers on all responses
    app.add_middleware(SecurityHeadersMiddleware)

    # Request body size limit
    app.add_middleware(RequestSizeLimitMiddleware)

    # API key auth (skip if no key configured — development mode)
    api_key = os.environ.get("REALIZE_API_KEY")
    if api_key:
        app.add_middleware(APIKeyMiddleware, api_key=api_key)
    else:
        logger.warning("REALIZE_API_KEY not set — API authentication is disabled (development mode)")

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Request logging (runs after RequestID so request_id is available)
    app.add_middleware(RequestLoggingMiddleware)

    # Request ID — outermost middleware, runs first
    app.add_middleware(RequestIDMiddleware)

    # --- Routes ---
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(systems.router, prefix="/api", tags=["Systems"])
    app.include_router(kb.router, prefix="/api", tags=["KB"])
    app.include_router(health.router, tags=["Health"])
    app.include_router(webhooks.router, tags=["Webhooks"])
    app.include_router(evolution.router, prefix="/api", tags=["Evolution"])

    return app


app = create_app()
