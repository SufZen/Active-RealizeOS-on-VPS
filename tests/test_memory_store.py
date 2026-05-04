"""Tests for realize_core.memory.store — memory database operations.

Covers:
- Database initialization and schema creation (tables, indexes, triggers)
- Memory storage and FTS5 search
- FTS5 query sanitization
- Memory deduplication
- Recency-weighted search results
- LLM usage logging and stats
- Feedback signal aggregation
- Database maintenance (ANALYZE, VACUUM)
"""

import sqlite3
from datetime import datetime, timedelta

import pytest
import realize_core.memory.store as store

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point the memory store at a temp database for every test."""
    db_path = tmp_path / "test_memory.db"
    monkeypatch.setattr(store, "DB_PATH", db_path)
    store.init_db()
    return db_path


# ---------------------------------------------------------------------------
# Database and schema
# ---------------------------------------------------------------------------


class TestInitDB:
    def test_creates_tables(self, isolated_db):
        conn = sqlite3.connect(str(isolated_db))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "memories" in tables
        assert "conversations" in tables
        assert "sessions" in tables
        assert "llm_usage" in tables
        assert "interaction_log" in tables
        conn.close()

    def test_creates_fts_table(self, isolated_db):
        conn = sqlite3.connect(str(isolated_db))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "memories_fts" in tables
        conn.close()

    def test_creates_indexes(self, isolated_db):
        conn = sqlite3.connect(str(isolated_db))
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_conv_lookup" in indexes
        assert "idx_memories_system_category" in indexes
        assert "idx_llm_usage_tenant_date" in indexes
        assert "idx_interaction_task_date" in indexes
        conn.close()

    def test_creates_triggers(self, isolated_db):
        conn = sqlite3.connect(str(isolated_db))
        triggers = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            ).fetchall()
        }
        assert "memories_ai" in triggers  # INSERT trigger
        assert "memories_ad" in triggers  # DELETE trigger
        assert "memories_au" in triggers  # UPDATE trigger
        conn.close()

    def test_init_is_idempotent(self):
        """Calling init_db twice should not raise."""
        store.init_db()
        store.init_db()

    def test_wal_mode_enabled(self, isolated_db):
        conn = sqlite3.connect(str(isolated_db))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()


# ---------------------------------------------------------------------------
# Memory storage and search
# ---------------------------------------------------------------------------


class TestStoreAndSearch:
    def test_store_and_retrieve(self):
        store.store_memory("sys1", "learning", "Python is great for AI")
        results = store.search_memories("Python", system_key="sys1")
        assert len(results) >= 1
        assert any("Python" in r["content"] for r in results)

    def test_search_filters_by_system_key(self):
        store.store_memory("sys1", "learning", "Alpha topic")
        store.store_memory("sys2", "learning", "Alpha topic different system")
        results = store.search_memories("Alpha", system_key="sys1")
        assert all(r["system_key"] == "sys1" for r in results)

    def test_search_without_system_key(self):
        store.store_memory("sys1", "learning", "Unique token xyzabc")
        results = store.search_memories("xyzabc")
        assert len(results) >= 1

    def test_search_no_results(self):
        results = store.search_memories("nonexistentterm12345")
        assert results == []

    def test_search_respects_limit(self):
        for i in range(10):
            store.store_memory("sys1", "learning", f"Memory number {i} about databases")
        results = store.search_memories("databases", system_key="sys1", limit=3)
        assert len(results) <= 3

    def test_store_with_tags(self):
        store.store_memory("sys1", "preference", "Dark mode preferred", tags=["ui", "theme"])
        results = store.search_memories("Dark mode", system_key="sys1")
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# FTS5 query sanitization
# ---------------------------------------------------------------------------


class TestFTSSanitization:
    def test_removes_special_chars(self):
        assert store._sanitize_fts_query('hello "world"') == "hello world"

    def test_removes_boolean_operators(self):
        assert store._sanitize_fts_query("hello AND world OR test") == "hello world test"

    def test_removes_parentheses(self):
        assert store._sanitize_fts_query("(hello) world") == "hello world"

    def test_empty_query_returns_empty(self):
        assert store._sanitize_fts_query("AND OR NOT") == ""

    def test_safe_query_unchanged(self):
        assert store._sanitize_fts_query("simple query") == "simple query"

    def test_special_chars_dont_crash_search(self):
        """FTS5 MATCH with special chars should not raise OperationalError."""
        store.store_memory("sys1", "learning", "Test content for safety")
        # These would normally crash FTS5 MATCH
        store.search_memories('"crash" OR (fail)', system_key="sys1")
        # Should return empty or results, not raise


# ---------------------------------------------------------------------------
# Memory deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_duplicate_skipped(self):
        store.store_memory("sys1", "learning", "Users prefer markdown tables for data")
        store.store_memory("sys1", "learning", "Users prefer markdown tables for data")
        results = store.search_memories("markdown tables", system_key="sys1")
        assert len(results) == 1

    def test_similar_content_skipped(self):
        store.store_memory("sys1", "learning", "Users prefer markdown tables for data display")
        store.store_memory("sys1", "learning", "Users prefer markdown tables for data showing")
        results = store.search_memories("markdown tables", system_key="sys1")
        # Should have only 1 due to >80% overlap
        assert len(results) == 1

    def test_different_content_not_skipped(self):
        store.store_memory("sys1", "learning", "Python is great for machine learning")
        store.store_memory("sys1", "learning", "JavaScript is used for web development")
        r1 = store.search_memories("Python machine learning", system_key="sys1")
        r2 = store.search_memories("JavaScript web", system_key="sys1")
        assert len(r1) >= 1
        assert len(r2) >= 1

    def test_different_category_not_deduped(self):
        store.store_memory("sys1", "learning", "Important topic about AI")
        store.store_memory("sys1", "decision", "Important topic about AI")
        # Both should exist since categories differ
        with store.db_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE system_key = ?", ("sys1",)
            ).fetchone()[0]
        assert count == 2


# ---------------------------------------------------------------------------
# Recency weighting
# ---------------------------------------------------------------------------


class TestRecencyWeighting:
    def test_recent_memories_ranked_higher(self):
        """Recent memories should appear before old ones."""
        # Insert an old memory directly
        old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
        with store.db_connection() as conn:
            conn.execute(
                "INSERT INTO memories (system_key, category, content, tags, created_at) VALUES (?, ?, ?, ?, ?)",
                ("sys1", "learning", "Old memory about search quality", "[]", old_date),
            )

        # Insert a recent memory via API
        store.store_memory("sys1", "learning", "New memory about search quality improvements")

        results = store.search_memories("search quality", system_key="sys1")
        assert len(results) >= 2
        # First result should be the newer one
        assert "New" in results[0]["content"] or "improvements" in results[0]["content"]


# ---------------------------------------------------------------------------
# LLM usage
# ---------------------------------------------------------------------------


class TestLLMUsage:
    def test_log_and_get_stats(self):
        store.log_llm_usage("claude-sonnet", 100, 200, 0.005, "tenant1")
        store.log_llm_usage("claude-sonnet", 150, 250, 0.008, "tenant1")
        stats = store.get_usage_stats("tenant1")
        assert stats["total_calls"] == 2
        assert stats["total_input_tokens"] == 250
        assert stats["total_output_tokens"] == 450

    def test_stats_filter_by_tenant(self):
        store.log_llm_usage("model-a", 100, 200, 0.01, "t1")
        store.log_llm_usage("model-b", 100, 200, 0.01, "t2")
        stats = store.get_usage_stats("t1")
        assert stats["total_calls"] == 1

    def test_stats_empty(self):
        stats = store.get_usage_stats("nonexistent")
        assert stats["total_calls"] == 0


# ---------------------------------------------------------------------------
# Feedback signals
# ---------------------------------------------------------------------------


class TestFeedbackSignals:
    def test_get_feedback(self):
        with store.db_connection() as conn:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO interaction_log (task_type, feedback_signal, created_at) VALUES (?, ?, ?)",
                ("content", "positive", now),
            )
            conn.execute(
                "INSERT INTO interaction_log (task_type, feedback_signal, created_at) VALUES (?, ?, ?)",
                ("content", "positive", now),
            )
            conn.execute(
                "INSERT INTO interaction_log (task_type, feedback_signal, created_at) VALUES (?, ?, ?)",
                ("content", "negative", now),
            )
        signals = store.get_feedback_signals("content")
        assert signals["positive"] == 2
        assert signals["negative"] == 1

    def test_feedback_empty(self):
        signals = store.get_feedback_signals("nonexistent_type")
        assert signals == {}


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------


class TestMaintenance:
    def test_maintenance_runs(self):
        """maintenance() should not raise on a valid database."""
        store.store_memory("sys1", "learning", "Test content")
        store.maintenance()  # Should not raise

    def test_maintenance_on_empty_db(self):
        """maintenance() should work even on an empty database."""
        store.maintenance()  # Should not raise
