"""Tests for realize_core.tools.kb_tools — kb_get, kb_search, kb_outline, kb_append."""

import pytest
from realize_core.tools.kb_tools import kb_append, kb_get, kb_outline, kb_search


@pytest.fixture
def kb_dir(tmp_path):
    """Create a minimal KB directory structure."""
    sys_dir = tmp_path / "systems" / "test-venture" / "B-brain"
    sys_dir.mkdir(parents=True)
    (sys_dir / "knowledge.md").write_text("# Test Knowledge\nThis is test knowledge content.")

    skills_dir = tmp_path / "systems" / "test-venture" / "R-routines" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "test-skill.yaml").write_text(
        "name: Test Skill\ndescription: A test skill\ntriggers: [test]\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# kb_get: path traversal guard
# ---------------------------------------------------------------------------


class TestKbGet:
    async def test_dotdot_traversal_rejected(self, kb_dir):
        result = await kb_get("../../etc/passwd", kb_path=str(kb_dir))
        assert result["status"] == "error"
        assert "traversal" in result["error"].lower() or "escapes" in result["error"].lower()

    async def test_read_existing_file(self, kb_dir):
        result = await kb_get("systems/test-venture/B-brain/knowledge.md", kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert "Test Knowledge" in result["content"]

    async def test_file_not_found(self, kb_dir):
        result = await kb_get("systems/test-venture/B-brain/missing.md", kb_path=str(kb_dir))
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    async def test_max_chars_truncation(self, kb_dir):
        result = await kb_get("systems/test-venture/B-brain/knowledge.md", max_chars=5, kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert result["truncated"] is True
        assert len(result["content"]) == 5

    async def test_no_truncation_for_short_file(self, kb_dir):
        result = await kb_get("systems/test-venture/B-brain/knowledge.md", max_chars=10000, kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert result["truncated"] is False


# ---------------------------------------------------------------------------
# kb_search: needs indexed DB
# ---------------------------------------------------------------------------


class TestKbSearch:
    async def test_search_returns_ok(self, kb_dir):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(kb_dir), db_path=kb_dir / "kb_index.db", force=True)
        result = await kb_search("knowledge", kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert "results" in result

    async def test_search_empty_query_returns_error_or_empty(self, kb_dir):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(kb_dir), db_path=kb_dir / "kb_index.db", force=True)
        result = await kb_search("", kb_path=str(kb_dir))
        # Empty query should not crash; may return empty results or error
        assert isinstance(result, dict)

    async def test_search_results_have_required_fields(self, kb_dir):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(kb_dir), db_path=kb_dir / "kb_index.db", force=True)
        result = await kb_search("test knowledge", kb_path=str(kb_dir))
        for r in result.get("results", []):
            assert "path" in r
            assert "title" in r
            assert "summary" in r
            # No full content in results
            assert "content" not in r


# ---------------------------------------------------------------------------
# kb_outline: needs indexed DB
# ---------------------------------------------------------------------------


class TestKbOutline:
    async def test_outline_returns_ok(self, kb_dir):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(kb_dir), db_path=kb_dir / "kb_index.db", force=True)
        result = await kb_outline(system_key="test-venture", kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert "resources" in result
        assert result["count"] >= 1

    async def test_outline_layer_filter(self, kb_dir):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(kb_dir), db_path=kb_dir / "kb_index.db", force=True)
        result = await kb_outline(system_key="test-venture", layer="B", kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert all(r["layer"] == "B" for r in result["resources"])

    async def test_outline_skill_yaml_included(self, kb_dir):
        from realize_core.kb.indexer import index_kb_files

        index_kb_files(str(kb_dir), db_path=kb_dir / "kb_index.db", force=True)
        result = await kb_outline(system_key="test-venture", kind="skill_yaml", kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert result["count"] >= 1


# ---------------------------------------------------------------------------
# kb_append: existing behaviour (unchanged)
# ---------------------------------------------------------------------------


class TestKbAppend:
    async def test_append_creates_file(self, kb_dir):
        result = await kb_append("systems/test-venture/notes.md", "# Note\nSome content.", kb_path=str(kb_dir))
        assert result["status"] == "ok"
        assert result["bytes_written"] > 0
        assert (kb_dir / "systems" / "test-venture" / "notes.md").exists()

    async def test_append_dotdot_rejected(self, kb_dir):
        result = await kb_append("../../etc/cron.d/evil", "evil", kb_path=str(kb_dir))
        assert result["status"] == "error"

    async def test_append_must_start_with_systems(self, kb_dir):
        result = await kb_append("shared/notes.md", "content", kb_path=str(kb_dir))
        assert result["status"] == "error"
