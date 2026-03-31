"""Tests for API route improvements: error handling, validation, health checks."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from realize_api.main import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    """Create a FastAPI client with startup dependencies mocked."""
    config = {
        "systems": [{"key": "test", "name": "Test", "directory": "systems/test"}],
        "shared": {
            "identity": "shared/identity.md",
            "preferences": "shared/user-preferences.md",
        },
        "features": {},
        "kb_path": str(tmp_path),
    }
    systems = {
        "test": {
            "name": "Test System",
            "agents": {"orchestrator": "systems/test/A-agents/orchestrator.md"},
            "routing": {"general": ["orchestrator"]},
        }
    }
    features = {}

    monkeypatch.delenv("REALIZE_API_KEY", raising=False)
    monkeypatch.delenv("REALIZE_DEBUG", raising=False)
    monkeypatch.setenv("MCP_ENABLED", "false")
    monkeypatch.setattr("realize_core.config.load_config", lambda config_path=None: config)
    monkeypatch.setattr("realize_core.config.build_systems_dict", lambda cfg, kb_path=None: systems)
    monkeypatch.setattr("realize_core.config.get_features", lambda cfg: features)
    monkeypatch.setattr("realize_core.memory.store.init_db", Mock())
    monkeypatch.setattr("realize_core.kb.indexer.index_kb_files", Mock())
    monkeypatch.setattr("realize_core.prompt.builder.warm_cache", Mock())
    monkeypatch.setattr("realize_core.skills.detector.reload_skills", Mock())

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Tests for the enhanced /health endpoint."""

    def test_health_returns_checks(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "checks" in data
        assert "systems_loaded" in data
        assert "uptime_seconds" in data

    def test_health_reports_config_status(self, api_client):
        resp = api_client.get("/health")
        data = resp.json()
        assert data["checks"]["config"] == "ok"

    def test_health_reports_llm_status(self, api_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        resp = api_client.get("/health")
        data = resp.json()
        assert data["checks"]["llm_anthropic"] == "configured"


# ---------------------------------------------------------------------------
# Chat error sanitization
# ---------------------------------------------------------------------------


class TestChatErrorSanitization:
    """Tests for chat endpoint error handling."""

    def test_chat_error_hides_details_in_production(self, api_client, monkeypatch):
        monkeypatch.delenv("REALIZE_DEBUG", raising=False)
        process_message = AsyncMock(side_effect=ValueError("/secret/path/leaked"))
        monkeypatch.setattr("realize_core.base_handler.process_message", process_message)

        resp = api_client.post(
            "/api/chat",
            json={"message": "test", "system_key": "test", "user_id": "u1"},
        )
        assert resp.status_code == 500
        assert "/secret/path" not in resp.json()["detail"]
        assert "Internal processing error" in resp.json()["detail"]

    def test_chat_error_shows_details_in_debug(self, api_client, monkeypatch):
        monkeypatch.setenv("REALIZE_DEBUG", "true")
        process_message = AsyncMock(side_effect=ValueError("debug info here"))
        monkeypatch.setattr("realize_core.base_handler.process_message", process_message)

        resp = api_client.post(
            "/api/chat",
            json={"message": "test", "system_key": "test", "user_id": "u1"},
        )
        assert resp.status_code == 500
        assert "debug info here" in resp.json()["detail"]

    def test_chat_system_not_found(self, api_client):
        resp = api_client.post(
            "/api/chat",
            json={"message": "test", "system_key": "nonexistent", "user_id": "u1"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Conversation limit validation
# ---------------------------------------------------------------------------


class TestConversationValidation:
    """Tests for query parameter validation."""

    @patch("realize_core.memory.conversation.get_history", return_value=[])
    def test_valid_limit(self, mock_hist, api_client):
        resp = api_client.get("/api/conversations/test/user1?limit=10")
        assert resp.status_code == 200

    def test_negative_limit_rejected(self, api_client):
        resp = api_client.get("/api/conversations/test/user1?limit=-1")
        assert resp.status_code == 422

    def test_excessive_limit_rejected(self, api_client):
        resp = api_client.get("/api/conversations/test/user1?limit=9999")
        assert resp.status_code == 422

    def test_zero_limit_rejected(self, api_client):
        resp = api_client.get("/api/conversations/test/user1?limit=0")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Evolution error handling
# ---------------------------------------------------------------------------


class TestEvolutionErrorHandling:
    """Tests for evolution endpoints returning proper HTTP status codes."""

    @patch(
        "realize_core.evolution.analytics.get_interaction_stats",
        side_effect=RuntimeError("db error"),
    )
    def test_analytics_error_returns_500(self, mock_stats, api_client):
        resp = api_client.get("/api/analytics/test?days=7")
        assert resp.status_code == 500
        # Should not leak internal details in production
        assert "db error" not in resp.json().get("detail", "")

    def test_analytics_invalid_days_rejected(self, api_client):
        resp = api_client.get("/api/analytics/test?days=0")
        assert resp.status_code == 422

    def test_analytics_excessive_days_rejected(self, api_client):
        resp = api_client.get("/api/analytics/test?days=999")
        assert resp.status_code == 422

    @patch(
        "realize_core.evolution.analytics.get_interaction_stats",
        side_effect=RuntimeError("db error"),
    )
    def test_all_analytics_error_returns_500(self, mock_stats, api_client):
        resp = api_client.get("/api/analytics?days=7")
        assert resp.status_code == 500

    def test_usage_invalid_days(self, api_client):
        resp = api_client.get("/api/usage?days=-5")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Evolution Pydantic validation
# ---------------------------------------------------------------------------


class TestEvolutionPydanticValidation:
    """Tests for Pydantic request model validation on evolution endpoints."""

    def test_refine_prompt_missing_fields(self, api_client):
        resp = api_client.post("/api/evolution/refine-prompt", json={})
        assert resp.status_code == 422

    def test_refine_prompt_valid_body(self, api_client, monkeypatch):
        mock_refine = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "realize_core.evolution.prompt_refiner.suggest_prompt_refinement",
            mock_refine,
        )
        resp = api_client.post(
            "/api/evolution/refine-prompt",
            json={
                "system_key": "test",
                "agent_key": "orchestrator",
                "patterns": ["too verbose"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "No prompt changes suggested"

    def test_apply_refinement_missing_fields(self, api_client):
        resp = api_client.post("/api/evolution/apply-refinement", json={})
        assert resp.status_code == 422

    def test_apply_refinement_valid_body(self, api_client, monkeypatch):
        mock_apply = AsyncMock(return_value="Applied successfully")
        monkeypatch.setattr(
            "realize_core.evolution.prompt_refiner.apply_prompt_refinement",
            mock_apply,
        )
        monkeypatch.setattr("realize_core.prompt.builder.clear_cache", Mock())

        resp = api_client.post(
            "/api/evolution/apply-refinement",
            json={
                "prompt_path": "systems/test/A-agents/orchestrator.md",
                "changes": [{"content": "Be concise", "location": "end", "type": "add"}],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"


# ---------------------------------------------------------------------------
# Webhook route ordering
# ---------------------------------------------------------------------------


class TestWebhookRouteOrdering:
    """Tests that trigger-skill doesn't get swallowed by the {endpoint_name} wildcard."""

    def test_trigger_skill_resolves(self, api_client):
        """POST /webhooks/trigger-skill should hit the trigger-skill handler, not the wildcard."""
        resp = api_client.post(
            "/webhooks/trigger-skill",
            json={"system_key": "test", "message": "hello"},
        )
        # Should get a response from trigger_skill_webhook, not a 404 "endpoint not registered"
        # (It may fail processing but the route itself should resolve)
        assert resp.status_code != 404 or "not registered" not in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# CORS defaults
# ---------------------------------------------------------------------------


class TestCORSDefaults:
    """Tests for CORS configuration."""

    def test_cors_default_not_wildcard(self, api_client, monkeypatch):
        """Default CORS should not be wildcard."""
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        # The app was created with default CORS — verify it's not wide open
        # by checking that a random origin gets rejected
        resp = api_client.options(
            "/api/chat",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # If CORS is properly restricted, the response won't include the evil origin
        allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
        assert allow_origin != "*"
