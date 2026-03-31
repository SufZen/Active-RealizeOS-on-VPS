"""Tests for realize_core.memory.conversation — conversation history management.

Covers:
- Message add/get lifecycle
- Conversation summarization and trimming
- SQLite write-through and hydration
- Topic-scoped conversations
- Cross-system context
- Cache eviction (LRU)
- clear_history with topic_id
- History with timestamps
"""

import sqlite3

import pytest
import realize_core.memory.conversation as conv
import realize_core.memory.store as store

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Reset conversation cache and point store at a temp database."""
    conv._conversations.clear()
    conv._hydrated.clear()
    db_path = tmp_path / "test_memory.db"
    monkeypatch.setattr(store, "DB_PATH", db_path)
    store.init_db()
    return db_path


# ---------------------------------------------------------------------------
# Basic add/get
# ---------------------------------------------------------------------------


class TestAddAndGet:
    def test_add_and_get_message(self):
        conv.add_message("sys1", "user1", "user", "Hello")
        conv.add_message("sys1", "user1", "assistant", "Hi there")
        history = conv.get_history("sys1", "user1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_get_history_strips_internal_fields(self):
        conv.add_message("sys1", "user1", "user", "Test")
        history = conv.get_history("sys1", "user1")
        assert "created_at" not in history[0]

    def test_get_history_with_limit(self):
        for i in range(10):
            conv.add_message("sys1", "user1", "user", f"Message {i}")
        history = conv.get_history("sys1", "user1", limit=3)
        assert len(history) == 3
        # Should be the 3 most recent
        assert history[-1]["content"] == "Message 9"

    def test_empty_history(self):
        history = conv.get_history("sys1", "user1")
        assert history == []


# ---------------------------------------------------------------------------
# Topic scoping
# ---------------------------------------------------------------------------


class TestTopicScoping:
    def test_separate_topics(self):
        conv.add_message("sys1", "user1", "user", "Topic A message", topic_id="topicA")
        conv.add_message("sys1", "user1", "user", "Topic B message", topic_id="topicB")
        history_a = conv.get_history("sys1", "user1", topic_id="topicA")
        history_b = conv.get_history("sys1", "user1", topic_id="topicB")
        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0]["content"] == "Topic A message"
        assert history_b[0]["content"] == "Topic B message"

    def test_default_topic_is_empty(self):
        conv.add_message("sys1", "user1", "user", "No topic")
        history = conv.get_history("sys1", "user1", topic_id="")
        assert len(history) == 1


# ---------------------------------------------------------------------------
# SQLite persistence and hydration
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_messages_persist_to_sqlite(self, isolated_env):
        conv.add_message("sys1", "user1", "user", "Persistent msg")
        # Verify in SQLite directly
        conn = sqlite3.connect(str(isolated_env))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM conversations").fetchall()
        assert len(rows) == 1
        assert rows[0]["content"] == "Persistent msg"
        conn.close()

    def test_hydration_from_sqlite(self, isolated_env):
        # Insert directly into SQLite (simulating a restart)
        conn = sqlite3.connect(str(isolated_env))
        conn.execute(
            "INSERT INTO conversations (bot_name, user_id, role, content, topic_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("sys1", "user1", "user", "From SQLite", "", "2025-01-01 00:00:00"),
        )
        conn.commit()
        conn.close()

        # Clear cache to force hydration
        conv._conversations.clear()
        conv._hydrated.clear()

        history = conv.get_history("sys1", "user1")
        assert len(history) == 1
        assert history[0]["content"] == "From SQLite"


# ---------------------------------------------------------------------------
# Summarization and trimming
# ---------------------------------------------------------------------------


class TestSummarization:
    def test_summarize_on_overflow(self):
        """When exceeding MAX_CONVERSATION_HISTORY, older messages should be summarized."""
        total = conv.MAX_CONVERSATION_HISTORY + 5
        for i in range(total):
            conv.add_message("sys1", "user1", "user", f"Message number {i}")

        key = ("sys1", "user1", "")
        messages = conv._conversations.get(key, [])
        # After summarization: summary + _KEEP_RECENT messages + any added after the trim
        # The trim triggers at MAX+1, leaving summary+8, then 4 more are added
        assert len(messages) < total
        # First message should be a summary
        assert messages[0]["content"].startswith(conv._SUMMARY_MARKER)

    def test_summary_preserves_recent(self):
        """Recent messages should be kept verbatim after summarization."""
        total = conv.MAX_CONVERSATION_HISTORY + 5
        for i in range(total):
            conv.add_message("sys1", "user1", "user", f"Msg-{i}")

        key = ("sys1", "user1", "")
        messages = conv._conversations.get(key, [])
        recent = messages[1:]  # Skip summary
        # Last message should be the most recently added
        assert recent[-1]["content"] == f"Msg-{total - 1}"


# ---------------------------------------------------------------------------
# Clear history
# ---------------------------------------------------------------------------


class TestClearHistory:
    def test_clear_removes_from_cache(self):
        conv.add_message("sys1", "user1", "user", "To be cleared")
        conv.clear_history("sys1", "user1")
        history = conv.get_history("sys1", "user1")
        assert history == []

    def test_clear_removes_from_sqlite(self, isolated_env):
        conv.add_message("sys1", "user1", "user", "To be cleared")
        conv.clear_history("sys1", "user1")
        conn = sqlite3.connect(str(isolated_env))
        count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE bot_name = ? AND user_id = ?",
            ("sys1", "user1"),
        ).fetchone()[0]
        assert count == 0
        conn.close()

    def test_clear_respects_topic_id(self, isolated_env):
        conv.add_message("sys1", "user1", "user", "Topic A", topic_id="a")
        conv.add_message("sys1", "user1", "user", "Topic B", topic_id="b")
        conv.clear_history("sys1", "user1", topic_id="a")

        # Topic A should be cleared
        history_a = conv.get_history("sys1", "user1", topic_id="a")
        assert history_a == []

        # Topic B should still exist
        # Need to clear hydrated state so it re-reads from SQLite
        conv._hydrated.discard(("sys1", "user1", "b"))
        if ("sys1", "user1", "b") in conv._conversations:
            del conv._conversations[("sys1", "user1", "b")]
        history_b = conv.get_history("sys1", "user1", topic_id="b")
        assert len(history_b) == 1

    def test_clear_all(self, isolated_env):
        conv.add_message("sys1", "user1", "user", "Msg 1")
        conv.add_message("sys2", "user2", "user", "Msg 2")
        conv.clear_all()
        assert len(conv._conversations) == 0
        assert len(conv._hydrated) == 0


# ---------------------------------------------------------------------------
# Cross-system context
# ---------------------------------------------------------------------------


class TestCrossSystem:
    def test_cross_system_includes_other_systems(self):
        conv.add_message("sys1", "user1", "user", "In system 1")
        conv.add_message("sys2", "user1", "user", "In system 2")
        cross = conv.get_cross_system_context("user1", ["sys1", "sys2"], exclude_system="sys1")
        assert len(cross) >= 1
        assert any("[From sys2]" in m["content"] for m in cross)

    def test_cross_system_excludes_current(self):
        conv.add_message("sys1", "user1", "user", "Current system")
        cross = conv.get_cross_system_context("user1", ["sys1"], exclude_system="sys1")
        assert cross == []


# ---------------------------------------------------------------------------
# Cache eviction
# ---------------------------------------------------------------------------


class TestCacheEviction:
    def test_eviction_at_limit(self):
        """Cache should evict LRU entries when exceeding _MAX_CACHE_KEYS."""
        original_limit = conv._MAX_CACHE_KEYS
        conv._MAX_CACHE_KEYS = 5
        try:
            for i in range(10):
                conv.add_message(f"sys{i}", "user1", "user", f"Message for sys{i}")

            # Should have at most 5 entries
            assert len(conv._conversations) <= 5
            # Most recent entries should be present
            assert ("sys9", "user1", "") in conv._conversations
        finally:
            conv._MAX_CACHE_KEYS = original_limit


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


class TestTimestamps:
    def test_get_history_with_timestamps(self):
        conv.add_message("sys1", "user1", "user", "Hello")
        history = conv.get_history_with_timestamps("sys1", "user1")
        assert len(history) == 1
        # Content should have a timestamp prefix
        assert history[0]["content"].startswith("[")

    def test_get_last_assistant_message(self):
        conv.add_message("sys1", "user1", "user", "Question")
        conv.add_message("sys1", "user1", "assistant", "Answer")
        last = conv.get_last_assistant_message("sys1", "user1")
        assert last == "Answer"

    def test_get_last_assistant_no_messages(self):
        last = conv.get_last_assistant_message("sys1", "user1")
        assert last is None
