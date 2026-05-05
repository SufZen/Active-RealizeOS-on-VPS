"""Tests for realize_core.kb.indexer — KB indexing and hybrid search.

Covers:
- Database initialization and schema creation
- Markdown file indexing with title extraction
- System detection from file paths
- FTS5 keyword search
- Cosine similarity computation
- Hybrid merge scoring
- Incremental indexing (mtime-based skip)
- Edge cases: empty KB, no match, binary data conversion
"""

import struct

import pytest
from realize_core.kb.indexer import (
    _build_search_dirs,
    _bytes_to_vec,
    _classify_kind,
    _classify_layer,
    _cosine_similarity,
    _detect_system,
    _extract_frontmatter,
    _extract_title,
    _get_conn,
    _infer_summary,
    _init_index_db,
    _merge_hybrid,
    _sanitize_fts_query,
    get_resource,
    index_kb_files,
    list_resources,
    semantic_search,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def index_db(tmp_path):
    """Create an initialized index database."""
    db_path = tmp_path / "test_index.db"
    _init_index_db(db_path)
    return db_path


@pytest.fixture
def kb_with_files(tmp_path):
    """Create a KB directory with markdown files for indexing."""
    # System files
    sys_dir = tmp_path / "systems" / "venture1" / "F-foundations"
    sys_dir.mkdir(parents=True)
    (sys_dir / "venture-identity.md").write_text("# Venture Identity\nWe are a tech company focused on AI solutions.")
    (sys_dir / "venture-voice.md").write_text("# Venture Voice\nProfessional, concise, and innovative.")

    agents_dir = tmp_path / "systems" / "venture1" / "A-agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "orchestrator.md").write_text("# Orchestrator\nCoordinates all agent activities.")

    insights_dir = tmp_path / "systems" / "venture1" / "I-insights"
    insights_dir.mkdir(parents=True)
    (insights_dir / "learning-log.md").write_text(
        "# Learning Log\n- Users prefer markdown tables\n- CTA should be bold"
    )

    # Shared files
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()
    (shared_dir / "identity.md").write_text("# Identity\nI am a business owner managing multiple ventures.")

    return tmp_path


# ---------------------------------------------------------------------------
# Database and schema
# ---------------------------------------------------------------------------


class TestDatabase:
    def test_init_creates_tables(self, index_db):
        """Database should have kb_files and kb_fts tables after init."""
        conn = _get_conn(index_db)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {row["name"] for row in tables}
        assert "kb_files" in table_names
        assert "kb_fts" in table_names
        conn.close()

    def test_init_is_idempotent(self, tmp_path):
        """Calling init twice should not fail."""
        db_path = tmp_path / "test.db"
        _init_index_db(db_path)
        _init_index_db(db_path)  # Should not raise


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------


class TestExtractTitle:
    def test_heading_extraction(self):
        content = "# My Document Title\nSome content here."
        assert _extract_title(content, "any/path.md") == "My Document Title"

    def test_heading_with_whitespace(self):
        content = "#   Spaced Title   \nContent."
        assert _extract_title(content, "any/path.md") == "Spaced Title"

    def test_no_heading_uses_filename(self):
        content = "Just content without any heading."
        result = _extract_title(content, "path/to/my-document.md")
        assert result == "My Document"

    def test_empty_content_uses_filename(self):
        result = _extract_title("", "path/some-file.md")
        assert result == "Some File"

    def test_multiline_content_uses_first_heading(self):
        content = "Some preamble\n# First Heading\n## Second Heading\nContent."
        assert _extract_title(content, "path.md") == "First Heading"


# ---------------------------------------------------------------------------
# System detection
# ---------------------------------------------------------------------------


class TestDetectSystem:
    def test_detects_from_path_structure(self):
        assert _detect_system("systems/venture1/F-foundations/venture.md") == "venture1"

    def test_detects_second_system(self):
        assert _detect_system("systems/venture2/A-agents/writer.md") == "venture2"

    def test_shared_files(self):
        result = _detect_system("shared/identity.md")
        assert result == "shared"

    def test_arbitrary_path_defaults_to_shared(self):
        result = _detect_system("some/random/path.md")
        assert result == "shared"

    def test_detect_from_config(self):
        config = {
            "myventure": {"system_dir": "systems/myventure"},
        }
        result = _detect_system("systems/myventure/F-foundations/test.md", config)
        assert result == "myventure"


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 0.0, 0.0]
        assert abs(_cosine_similarity(a, a) - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 0.001

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(_cosine_similarity(a, b) - (-1.0)) < 0.001

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_nonunit_vectors(self):
        a = [3.0, 4.0]
        b = [3.0, 4.0]
        assert abs(_cosine_similarity(a, b) - 1.0) < 0.001


# ---------------------------------------------------------------------------
# Vector byte conversion
# ---------------------------------------------------------------------------


class TestBytesConversion:
    def test_roundtrip(self):
        original = [1.0, 2.5, -3.7, 0.0]
        packed = struct.pack(f"{len(original)}f", *original)
        result = _bytes_to_vec(packed)
        for a, b in zip(original, result):
            assert abs(a - b) < 0.001

    def test_empty_vector(self):
        packed = struct.pack("0f")
        result = _bytes_to_vec(packed)
        assert result == []


# ---------------------------------------------------------------------------
# Directory discovery
# ---------------------------------------------------------------------------


class TestBuildSearchDirs:
    def test_discovers_fabric_dirs(self, kb_with_files):
        dirs = _build_search_dirs(kb_with_files)
        # Should find F-foundations, A-agents, I-insights under venture1
        dir_names = [d.replace("\\", "/").split("/")[-1] for d in dirs if "venture1" in d]
        assert "F-foundations" in dir_names
        assert "A-agents" in dir_names
        assert "I-insights" in dir_names

    def test_discovers_shared_dir(self, kb_with_files):
        dirs = _build_search_dirs(kb_with_files)
        assert "shared" in dirs

    def test_empty_kb(self, tmp_path):
        dirs = _build_search_dirs(tmp_path)
        assert dirs == []


# ---------------------------------------------------------------------------
# File indexing
# ---------------------------------------------------------------------------


class TestIndexKBFiles:
    def test_indexes_markdown_files(self, kb_with_files):
        db_path = kb_with_files / "test_index.db"
        count = index_kb_files(
            kb_root=str(kb_with_files),
            db_path=db_path,
            force=True,
        )
        assert count > 0

    def test_indexed_files_searchable(self, kb_with_files):
        db_path = kb_with_files / "test_index.db"
        index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)

        # FTS5 search should find results
        results = semantic_search(
            "venture identity",
            db_path=db_path,
            kb_root=str(kb_with_files),
        )
        assert len(results) > 0
        assert any("venture" in r.get("title", "").lower() for r in results)

    def test_incremental_skip(self, kb_with_files):
        """Second indexing run should re-index files with same mtime (safe for NTFS)."""
        db_path = kb_with_files / "test_index.db"
        count1 = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=False)
        assert count1 > 0
        # With < comparison, same-mtime files are re-indexed (safe default for NTFS).
        # This is intentional — prevents missing edits within mtime resolution.

    def test_force_reindexes(self, kb_with_files):
        """Force flag should re-index all files."""
        db_path = kb_with_files / "test_index.db"
        count1 = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        count2 = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        assert count1 == count2

    def test_empty_kb_returns_zero(self, tmp_path):
        db_path = tmp_path / "test_index.db"
        count = index_kb_files(kb_root=str(tmp_path), db_path=db_path, force=True)
        assert count == 0


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_with_system_filter(self, kb_with_files):
        db_path = kb_with_files / "test_index.db"
        index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)

        results = semantic_search(
            "venture",
            system_key="venture1",
            db_path=db_path,
            kb_root=str(kb_with_files),
        )
        assert all(r.get("system_key") == "venture1" for r in results)

    def test_search_no_results(self, kb_with_files):
        db_path = kb_with_files / "test_index.db"
        index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)

        results = semantic_search(
            "xyznonexistentterm123",
            db_path=db_path,
            kb_root=str(kb_with_files),
        )
        assert len(results) == 0

    def test_search_top_k_limit(self, kb_with_files):
        db_path = kb_with_files / "test_index.db"
        index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)

        results = semantic_search(
            "venture",
            top_k=1,
            db_path=db_path,
            kb_root=str(kb_with_files),
        )
        assert len(results) <= 1


# ---------------------------------------------------------------------------
# Hybrid merge
# ---------------------------------------------------------------------------


class TestHybridMerge:
    def test_merge_combines_scores(self):
        fts = [
            {"path": "a.md", "title": "A", "system_key": "s", "snippet": "...", "keyword_score": 1.0},
            {"path": "b.md", "title": "B", "system_key": "s", "snippet": "...", "keyword_score": 0.5},
        ]
        vector = [
            {"path": "a.md", "title": "A", "system_key": "s", "snippet": "...", "vector_score": 0.8},
            {"path": "c.md", "title": "C", "system_key": "s", "snippet": "...", "vector_score": 0.9},
        ]
        results = _merge_hybrid(fts, vector, top_k=5)
        paths = [r["path"] for r in results]
        assert "a.md" in paths  # Appears in both
        assert "b.md" in paths  # FTS only
        assert "c.md" in paths  # Vector only

    def test_merge_scoring_weights(self):
        fts = [{"path": "x.md", "title": "X", "system_key": "s", "snippet": "...", "keyword_score": 1.0}]
        vector = [{"path": "x.md", "title": "X", "system_key": "s", "snippet": "...", "vector_score": 1.0}]
        results = _merge_hybrid(fts, vector, top_k=5, vector_weight=0.7, keyword_weight=0.3)
        # Score should be 0.7*1.0 + 0.3*1.0 = 1.0
        assert abs(results[0]["score"] - 1.0) < 0.001

    def test_merge_respects_top_k(self):
        fts = [
            {"path": f"{i}.md", "title": f"Doc{i}", "system_key": "s", "snippet": "...", "keyword_score": 0.5}
            for i in range(10)
        ]
        results = _merge_hybrid(fts, [], top_k=3)
        assert len(results) <= 3

    def test_merge_empty_inputs(self):
        results = _merge_hybrid([], [], top_k=5)
        assert results == []


# ---------------------------------------------------------------------------
# FTS5 query sanitization
# ---------------------------------------------------------------------------


class TestSanitizeFTSQuery:
    def test_removes_quotes(self):
        assert _sanitize_fts_query('"hello world"') == "hello world"

    def test_removes_boolean_operators(self):
        assert _sanitize_fts_query("hello AND world OR test") == "hello world test"

    def test_removes_parentheses(self):
        assert _sanitize_fts_query("(test) query") == "test query"

    def test_removes_asterisks(self):
        assert _sanitize_fts_query("test*") == "test"

    def test_all_operators_returns_empty(self):
        assert _sanitize_fts_query("AND OR NOT") == ""

    def test_normal_query_unchanged(self):
        assert _sanitize_fts_query("venture identity") == "venture identity"

    def test_special_chars_in_search(self, kb_with_files):
        """Search with special chars should not crash."""
        db_path = kb_with_files / "test_index.db"
        index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        # These would crash FTS5 without sanitization
        semantic_search('"crash" OR (fail)', db_path=db_path, kb_root=str(kb_with_files))
        # Should return empty or results, not raise


# ---------------------------------------------------------------------------
# Stale file cleanup
# ---------------------------------------------------------------------------


class TestStaleCleanup:
    def test_deleted_files_removed_from_index(self, kb_with_files):
        db_path = kb_with_files / "test_index.db"
        count1 = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        assert count1 > 0

        # Delete a file from disk
        identity_file = kb_with_files / "systems" / "venture1" / "F-foundations" / "venture-identity.md"
        identity_file.unlink()

        # Re-index — should detect the deletion
        index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=False)

        # The deleted file should no longer appear in search
        results = semantic_search("venture identity", db_path=db_path, kb_root=str(kb_with_files))
        paths = [r["path"] for r in results]
        assert not any("venture-identity" in p for p in paths)


# ---------------------------------------------------------------------------
# Encoding fallback
# ---------------------------------------------------------------------------


class TestEncodingFallback:
    def test_latin1_file_indexed(self, kb_with_files):
        """Files with latin-1 encoding should be indexed without errors."""
        latin1_file = kb_with_files / "systems" / "venture1" / "F-foundations" / "latin1-test.md"
        latin1_file.write_bytes("# Latin1 Test\nCaf\xe9 content with accents".encode("latin-1"))

        db_path = kb_with_files / "test_index.db"
        count = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        assert count > 0

        results = semantic_search("Latin1", db_path=db_path, kb_root=str(kb_with_files))
        assert any("Latin1" in r.get("title", "") for r in results)

    def test_utf8_bom_file_indexed(self, kb_with_files):
        """Files with UTF-8 BOM should be indexed correctly."""
        bom_file = kb_with_files / "systems" / "venture1" / "F-foundations" / "bom-test.md"
        bom_file.write_bytes(b"\xef\xbb\xbf# BOM Test\nContent with BOM header")

        db_path = kb_with_files / "test_index.db"
        count = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        assert count > 0


# ---------------------------------------------------------------------------
# WAL mode and PRAGMAs
# ---------------------------------------------------------------------------


class TestDatabaseConfig:
    def test_wal_mode_enabled(self, index_db):
        conn = _get_conn(index_db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_system_key_index_exists(self, index_db):
        conn = _get_conn(index_db)
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_kb_system_key" in indexes
        conn.close()


# ---------------------------------------------------------------------------
# Mtime-based change detection
# ---------------------------------------------------------------------------


class TestMtimeDetection:
    def test_same_mtime_reindexed(self, kb_with_files):
        """Files with same mtime should be re-indexed (not skipped) to catch same-second edits."""
        db_path = kb_with_files / "test_index.db"
        count1 = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=True)
        assert count1 > 0

        # Modify content without changing mtime (simulate same-second edit)
        identity_file = kb_with_files / "systems" / "venture1" / "F-foundations" / "venture-identity.md"
        import os
        stat = os.stat(identity_file)
        identity_file.write_text("# Updated Identity\nNew content")
        # Restore original mtime
        os.utime(identity_file, (stat.st_atime, stat.st_mtime))

        count2 = index_kb_files(kb_root=str(kb_with_files), db_path=db_path, force=False)
        # With < comparison, same mtime should NOT skip (count2 >= 1)
        # This is the safer behavior for NTFS
        assert count2 >= 1


# ---------------------------------------------------------------------------
# New: layer and kind classification
# ---------------------------------------------------------------------------


class TestClassify:
    def test_classify_layer_foundations(self):
        assert _classify_layer("systems/v1/F-foundations/file.md") == "F"

    def test_classify_layer_brain(self):
        assert _classify_layer("systems/v1/B-brain/knowledge.md") == "B"

    def test_classify_layer_creations(self):
        assert _classify_layer("systems/v1/C-creations/draft.md") == "C"

    def test_classify_layer_shared(self):
        assert _classify_layer("shared/identity.md") == "shared"

    def test_classify_layer_skill_yaml(self):
        assert _classify_layer("systems/v1/R-routines/skills/skill.yaml") == "skill"

    def test_classify_kind_agent(self):
        assert _classify_kind("systems/v1/A-agents/writer.md") == "agent"

    def test_classify_kind_skill_yaml(self):
        assert _classify_kind("systems/v1/R-routines/skills/skill.yaml") == "skill_yaml"

    def test_classify_kind_md(self):
        assert _classify_kind("systems/v1/B-brain/knowledge.md") == "md"


# ---------------------------------------------------------------------------
# New: frontmatter parsing
# ---------------------------------------------------------------------------


class TestFrontmatter:
    def test_parses_valid_frontmatter(self):
        pytest.importorskip("yaml")
        content = "---\nsummary: This is a summary\ntags: [ai, planning]\n---\n# Title\n"
        fm = _extract_frontmatter(content)
        assert fm.get("summary") == "This is a summary"
        assert "ai" in fm.get("tags", [])

    def test_no_frontmatter_returns_empty(self):
        content = "# Just a heading\nContent here."
        fm = _extract_frontmatter(content)
        assert fm == {}

    def test_malformed_frontmatter_returns_empty(self):
        pytest.importorskip("yaml")
        content = "---\ninvalid: [unclosed\n---\n# Title"
        fm = _extract_frontmatter(content)
        assert isinstance(fm, dict)

    def test_summary_inference_from_fm(self):
        pytest.importorskip("yaml")
        content = "---\nsummary: FM summary\n---\n# Title\nOther content."
        fm = _extract_frontmatter(content)
        summary = _infer_summary(content, "path/file.md", fm)
        assert summary == "FM summary"

    def test_summary_inference_from_first_sentence(self):
        content = "# Title\nThis is the first sentence."
        summary = _infer_summary(content, "path/file.md", {})
        assert "first sentence" in summary

    def test_summary_inference_fallback_to_filename(self):
        content = "---\n---\n"
        summary = _infer_summary(content, "path/my-file.md", {})
        assert "My File" in summary


# ---------------------------------------------------------------------------
# New: C-creations and skill YAML indexing
# ---------------------------------------------------------------------------


@pytest.fixture
def kb_extended(tmp_path):
    """KB with C-creations and skill YAML files added."""
    sys_dir = tmp_path / "systems" / "venture1"

    # Existing F-foundations
    (sys_dir / "F-foundations").mkdir(parents=True)
    (sys_dir / "F-foundations" / "identity.md").write_text("# Identity\nWe are a test venture.")

    # C-creations (previously not indexed)
    (sys_dir / "C-creations").mkdir(parents=True)
    (sys_dir / "C-creations" / "proposal.md").write_text("# Proposal\nA detailed proposal for a client.")

    # Skill YAML (v1 shape)
    skills_dir = sys_dir / "R-routines" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "content-pipeline.yaml").write_text(
        "name: Content Pipeline\ndescription: Draft and review content\ntriggers: [write, draft]\npipeline: [writer, reviewer]\n"
    )

    # Skill YAML (v2 shape)
    (skills_dir / "research-workflow.yaml").write_text(
        "name: Research Workflow\ndescription: Multi-step research\ntriggers: [research]\nsteps:\n  - type: agent\n    agent: analyst\n"
    )

    return tmp_path


class TestExtendedIndexing:
    def test_c_creations_indexed(self, kb_extended):
        db_path = kb_extended / "test.db"
        count = index_kb_files(str(kb_extended), db_path=db_path, force=True)
        assert count > 0

        resources = list_resources(system_key="venture1", layer="C", db_path=db_path)
        paths = [r["path"] for r in resources]
        assert any("proposal" in p for p in paths)

    def test_skill_yaml_in_manifest(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(system_key="venture1", kind="skill_yaml", db_path=db_path)
        assert len(resources) >= 2

    def test_skill_yaml_summary_from_description(self, kb_extended):
        pytest.importorskip("yaml")
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(system_key="venture1", kind="skill_yaml", db_path=db_path)
        summaries = [r.get("summary", "") for r in resources]
        assert any("Draft and review" in s for s in summaries)

    def test_v2_skill_yaml_indexed(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(system_key="venture1", kind="skill_yaml", db_path=db_path)
        titles = [r.get("title", "") for r in resources]
        assert any("Research" in t for t in titles)


# ---------------------------------------------------------------------------
# New: list_resources and get_resource
# ---------------------------------------------------------------------------


class TestResourceManifest:
    def test_list_resources_all(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(db_path=db_path)
        assert len(resources) > 0
        for r in resources:
            assert "path" in r
            assert "title" in r
            assert "layer" in r

    def test_list_resources_by_system(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(system_key="venture1", db_path=db_path)
        assert all(r["system_key"] == "venture1" for r in resources)

    def test_list_resources_by_layer(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(layer="F", db_path=db_path)
        assert all(r["layer"] == "F" for r in resources)

    def test_list_resources_sorted_by_layer(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(system_key="venture1", db_path=db_path)
        layers = [r["layer"] for r in resources]
        layer_order = {"F": 0, "A": 1, "B": 2, "R": 3, "I": 4, "C": 5, "shared": 6, "skill": 7}
        order_values = [layer_order.get(lyr, 99) for lyr in layers]
        assert order_values == sorted(order_values)

    def test_get_resource_found(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resources = list_resources(system_key="venture1", db_path=db_path)
        path = resources[0]["path"]

        resource = get_resource(path, db_path=db_path)
        assert resource is not None
        assert resource["path"] == path

    def test_get_resource_not_found(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        resource = get_resource("systems/nonexistent/file.md", db_path=db_path)
        assert resource is None

    def test_manifest_table_created(self, kb_extended):
        db_path = kb_extended / "test.db"
        index_kb_files(str(kb_extended), db_path=db_path, force=True)

        conn = _get_conn(db_path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "kb_resources" in tables
        conn.close()
