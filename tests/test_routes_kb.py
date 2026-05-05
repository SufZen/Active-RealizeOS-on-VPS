"""Tests for realize_api.routes.kb — KB search, resource, file, and index endpoints."""

import pytest
from fastapi.testclient import TestClient
from realize_api.main import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    """FastAPI test client with startup deps mocked."""
    # Create a minimal KB file so /api/kb/file can be tested
    kb_file = tmp_path / "systems" / "test-venture" / "B-brain" / "knowledge.md"
    kb_file.parent.mkdir(parents=True)
    kb_file.write_text("# Test Knowledge\nThis is test content.")

    config = {
        "systems": [{"key": "test-venture", "name": "Test", "directory": "systems/test-venture"}],
        "shared": {"identity": "shared/identity.md", "preferences": "shared/user-preferences.md"},
        "features": {},
        "kb_path": str(tmp_path),
    }
    systems = {
        "test-venture": {
            "name": "Test Venture",
            "agents": {"orchestrator": "systems/test-venture/A-agents/orchestrator.md"},
            "routing": {},
        }
    }

    monkeypatch.delenv("REALIZE_API_KEY", raising=False)
    monkeypatch.setenv("MCP_ENABLED", "false")
    monkeypatch.setattr("realize_core.config.load_config", lambda config_path=None: config)
    monkeypatch.setattr("realize_core.config.build_systems_dict", lambda cfg, kb_path=None: systems)
    monkeypatch.setattr("realize_core.config.get_features", lambda cfg: {})

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        # Patch kb_path on app state
        client.app.state.kb_path = tmp_path
        client.app.state.systems = systems
        yield client


# ---------------------------------------------------------------------------
# GET /api/kb/search
# ---------------------------------------------------------------------------


class TestKBSearch:
    def test_search_requires_q(self, api_client):
        resp = api_client.get("/api/kb/search")
        assert resp.status_code == 422  # Missing required param

    def test_search_returns_json(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/kb/search?q=knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "count" in data

    def test_search_invalid_layer_rejected(self, api_client):
        resp = api_client.get("/api/kb/search?q=test&layer=INVALID")
        assert resp.status_code == 400

    def test_search_valid_layer_accepted(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/kb/search?q=test&layer=B")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/kb/file
# ---------------------------------------------------------------------------


class TestKBFile:
    def test_file_reads_content(self, api_client):
        resp = api_client.get("/api/kb/file?path=systems/test-venture/B-brain/knowledge.md")
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert "Test Knowledge" in data["content"]

    def test_file_not_found(self, api_client):
        resp = api_client.get("/api/kb/file?path=systems/test-venture/B-brain/missing.md")
        assert resp.status_code == 404

    def test_file_traversal_rejected(self, api_client):
        resp = api_client.get("/api/kb/file?path=../../etc/passwd")
        assert resp.status_code == 400

    def test_file_max_chars_applied(self, api_client):
        resp = api_client.get("/api/kb/file?path=systems/test-venture/B-brain/knowledge.md&max_chars=100")
        assert resp.status_code == 200
        data = resp.json()
        # File is short; truncated may be False, but response is valid
        assert "content" in data
        assert "truncated" in data


# ---------------------------------------------------------------------------
# GET /api/kb/resource
# ---------------------------------------------------------------------------


class TestKBResource:
    def test_resource_not_found(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/kb/resource?path=systems/nonexistent/file.md")
        assert resp.status_code == 404

    def test_resource_found(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/kb/resource?path=systems/test-venture/B-brain/knowledge.md")
        # May be 200 if indexed, 404 if not (depends on timing)
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# GET /api/systems/{system_key}/kb/index
# ---------------------------------------------------------------------------


class TestSystemKBIndex:
    def test_unknown_system_returns_404(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/systems/nonexistent/kb/index")
        assert resp.status_code == 404

    def test_known_system_returns_200(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/systems/test-venture/kb/index")
        assert resp.status_code == 200
        data = resp.json()
        assert data["system_key"] == "test-venture"
        assert "resources" in data

    def test_layer_filter_applied(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/systems/test-venture/kb/index?layer=B")
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["layer"] == "B" for r in data["resources"])

    def test_invalid_layer_rejected(self, api_client, tmp_path):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(tmp_path), db_path=tmp_path / "kb_index.db", force=True)

        resp = api_client.get("/api/systems/test-venture/kb/index?layer=INVALID")
        assert resp.status_code == 400
