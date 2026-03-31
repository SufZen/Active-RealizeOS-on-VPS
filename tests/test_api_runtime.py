"""Runtime tests for FastAPI entrypoints and startup behavior."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from realize_api.main import create_app


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    """Create a FastAPI client with startup dependencies mocked."""
    config = {
        "systems": [{"key": "alpha", "name": "Alpha", "directory": "systems/alpha"}],
        "shared": {
            "identity": "shared/identity.md",
            "preferences": "shared/user-preferences.md",
        },
        "features": {"review_pipeline": True},
        "kb_path": str(tmp_path),
    }
    systems = {
        "alpha": {
            "name": "Alpha",
            "agents": {"orchestrator": "systems/alpha/A-agents/orchestrator.md"},
            "routing": {"general": ["orchestrator"]},
        }
    }
    features = {
        "review_pipeline": True,
        "auto_memory": True,
        "proactive_mode": True,
        "cross_system": False,
    }

    monkeypatch.delenv("REALIZE_API_KEY", raising=False)
    monkeypatch.setenv("MCP_ENABLED", "false")
    monkeypatch.setattr("realize_core.config.load_config", lambda config_path=None: config)
    monkeypatch.setattr("realize_core.config.build_systems_dict", lambda cfg, kb_path=None: systems)
    monkeypatch.setattr("realize_core.config.get_features", lambda cfg: features)
    monkeypatch.setattr("realize_core.memory.store.init_db", Mock())
    monkeypatch.setattr("realize_core.kb.indexer.index_kb_files", Mock())
    monkeypatch.setattr("realize_core.prompt.builder.warm_cache", Mock())
    monkeypatch.setattr("realize_core.skills.detector.reload_skills", Mock())

    app = create_app()
    with TestClient(app) as client:
        yield client, app, config, systems, features


def test_chat_route_passes_agent_override_and_features(api_client, monkeypatch):
    client, _app, _config, _systems, features = api_client
    process_message = AsyncMock(return_value="runtime response")

    monkeypatch.setattr("realize_core.base_handler.process_message", process_message)

    response = client.post(
        "/api/chat",
        json={
            "message": "Write something helpful",
            "system_key": "alpha",
            "user_id": "user-1",
            "agent_key": "writer",
            "channel": "api",
        },
    )

    assert response.status_code == 200
    assert response.json()["response"] == "runtime response"
    kwargs = process_message.await_args.kwargs
    assert kwargs["agent_key"] == "writer"
    assert kwargs["features"] == features


def test_system_skills_route_uses_runtime_helper(api_client, monkeypatch):
    client, _app, _config, _systems, _features = api_client

    monkeypatch.setattr(
        "realize_core.skills.detector.get_skills_for_system",
        lambda system_key, kb_path=None: [
            {"name": "research_workflow", "triggers": ["research"], "_version": 2},
        ],
    )

    response = client.get("/api/systems/alpha/skills")

    assert response.status_code == 200
    body = response.json()
    assert body["system_key"] == "alpha"
    assert body["skills"][0]["name"] == "research_workflow"
    assert body["skills"][0]["version"] == 2


def test_system_reload_refreshes_runtime_state(api_client, monkeypatch, tmp_path):
    client, app, _config, _systems, _features = api_client

    new_config = {
        "systems": [{"key": "beta", "name": "Beta", "directory": "systems/beta"}],
        "shared": {
            "identity": "shared/new-identity.md",
            "preferences": "shared/new-preferences.md",
        },
        "features": {"cross_system": True},
        "kb_path": str(tmp_path / "next-kb"),
    }
    new_systems = {
        "beta": {
            "name": "Beta",
            "agents": {"orchestrator": "systems/beta/A-agents/orchestrator.md"},
            "routing": {"general": ["orchestrator"]},
        }
    }
    new_features = {
        "review_pipeline": True,
        "auto_memory": True,
        "proactive_mode": True,
        "cross_system": True,
    }

    clear_cache = Mock()
    warm_cache = Mock()
    reload_skills = Mock()

    monkeypatch.setattr("realize_core.config.load_config", lambda config_path=None: new_config)
    monkeypatch.setattr("realize_core.config.build_systems_dict", lambda cfg, kb_path=None: new_systems)
    monkeypatch.setattr("realize_core.config.get_features", lambda cfg: new_features)
    monkeypatch.setattr("realize_core.prompt.builder.clear_cache", clear_cache)
    monkeypatch.setattr("realize_core.prompt.builder.warm_cache", warm_cache)
    monkeypatch.setattr("realize_core.skills.detector.reload_skills", reload_skills)

    response = client.post("/api/systems/reload")

    assert response.status_code == 200
    assert response.json()["systems"] == ["beta"]
    assert app.state.systems == new_systems
    assert app.state.shared_config == new_config["shared"]
    assert app.state.features == new_features
    assert app.state.kb_path == Path(new_config["kb_path"]).resolve()
    clear_cache.assert_called_once()
    reload_skills.assert_called_once_with(kb_path=Path(new_config["kb_path"]).resolve())
    warm_cache.assert_called_once()


def test_api_startup_uses_mcp_env_flag(monkeypatch, tmp_path):
    """MCP startup should be controlled by MCP_ENABLED, not YAML feature drift."""
    config = {
        "systems": [{"key": "alpha", "name": "Alpha", "directory": "systems/alpha"}],
        "shared": {
            "identity": "shared/identity.md",
            "preferences": "shared/user-preferences.md",
        },
        "features": {},
        "kb_path": str(tmp_path),
    }
    systems = {
        "alpha": {
            "name": "Alpha",
            "agents": {"orchestrator": "systems/alpha/A-agents/orchestrator.md"},
            "routing": {"general": ["orchestrator"]},
        }
    }

    initialize_mcp = AsyncMock()
    shutdown_mcp = AsyncMock()

    monkeypatch.delenv("REALIZE_API_KEY", raising=False)
    monkeypatch.setenv("MCP_ENABLED", "true")
    monkeypatch.setattr("realize_core.config.load_config", lambda config_path=None: config)
    monkeypatch.setattr("realize_core.config.build_systems_dict", lambda cfg, kb_path=None: systems)
    monkeypatch.setattr("realize_core.config.get_features", lambda cfg: {})
    monkeypatch.setattr("realize_core.memory.store.init_db", Mock())
    monkeypatch.setattr("realize_core.kb.indexer.index_kb_files", Mock())
    monkeypatch.setattr("realize_core.prompt.builder.warm_cache", Mock())
    monkeypatch.setattr("realize_core.skills.detector.reload_skills", Mock())
    monkeypatch.setattr("realize_core.tools.mcp.initialize_mcp", initialize_mcp)
    monkeypatch.setattr("realize_core.tools.mcp.shutdown_mcp", shutdown_mcp)

    app = create_app()
    with TestClient(app):
        pass

    initialize_mcp.assert_awaited_once()
    shutdown_mcp.assert_awaited_once()
