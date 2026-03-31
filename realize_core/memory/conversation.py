"""
Conversation History Manager for RealizeOS.

Maintains per-user, per-system conversation buffers with cross-system context sharing.
Uses SQLite write-through with in-memory cache for persistence across restarts.
Supports thread/topic scoping via optional topic_id parameter.
"""

import logging
from collections import OrderedDict
from datetime import datetime

logger = logging.getLogger(__name__)

# Default max conversation history length
MAX_CONVERSATION_HISTORY = 20

# Maximum number of conversation keys to keep in the in-memory cache
_MAX_CACHE_KEYS = 100

# In-memory cache: {(system_key, user_id, topic_id): [{"role": ..., "content": ...}]}
# Using OrderedDict for LRU eviction
_conversations: OrderedDict[tuple[str, str, str], list[dict]] = OrderedDict()

# Track which keys have been hydrated from SQLite
_hydrated: set[tuple[str, str, str]] = set()


def _db_ctx():
    """Get a SQLite connection context manager from memory store."""
    from realize_core.memory.store import db_connection

    return db_connection()


def _touch_cache(key: tuple):
    """Move a key to the end of the OrderedDict (most recently used) and evict if over limit."""
    if key in _conversations:
        _conversations.move_to_end(key)
    # Evict least recently used entries if over limit
    while len(_conversations) > _MAX_CACHE_KEYS:
        evicted_key, _ = _conversations.popitem(last=False)
        _hydrated.discard(evicted_key)


def _hydrate_if_needed(system_key: str, user_id: str, topic_id: str = ""):
    """Lazy-load conversation history from SQLite if not already in cache."""
    key = (system_key, user_id, topic_id)
    if key in _hydrated:
        _touch_cache(key)
        return

    try:
        with _db_ctx() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM conversations "
                "WHERE bot_name = ? AND user_id = ? AND COALESCE(topic_id, '') = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (system_key, user_id, topic_id, MAX_CONVERSATION_HISTORY),
            ).fetchall()

        if rows:
            _conversations[key] = [
                {"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in reversed(rows)
            ]
            logger.info(f"Hydrated {len(rows)} messages for {system_key}:{user_id}:{topic_id}")
    except Exception as e:
        logger.warning(f"Failed to hydrate conversation for {system_key}:{user_id}: {e}")

    _hydrated.add(key)
    _touch_cache(key)


def get_history(system_key: str, user_id: str, topic_id: str = "", limit: int = None) -> list[dict]:
    """
    Get conversation history for a specific user and system.
    Args:
        system_key: System identifier
        user_id: User identifier
        topic_id: Thread/topic ID (empty string for regular chats)
        limit: Max number of most recent messages to return (None = all)
    Returns:
        List of message dicts: [{"role": "user"/"assistant", "content": "..."}]
    """
    _hydrate_if_needed(system_key, user_id, topic_id)
    key = (system_key, user_id, topic_id)
    # Strip internal fields (created_at) — LLM APIs reject extra keys
    history = [{"role": m["role"], "content": m["content"]} for m in _conversations.get(key, [])]
    if limit is not None:
        history = history[-limit:]
    return history


def add_message(system_key: str, user_id: str, role: str, content: str, topic_id: str = ""):
    """
    Add a message to the conversation history.
    Writes to both in-memory cache and SQLite.
    When history exceeds MAX_CONVERSATION_HISTORY, summarizes older messages
    rather than discarding them entirely.
    """
    _hydrate_if_needed(system_key, user_id, topic_id)
    key = (system_key, user_id, topic_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if key not in _conversations:
        _conversations[key] = []
    _conversations[key].append({"role": role, "content": content, "created_at": now})
    _touch_cache(key)  # Ensure LRU tracking and eviction after insert

    # Summarize-then-trim: when exceeding limit, summarize older messages
    if len(_conversations[key]) > MAX_CONVERSATION_HISTORY:
        _summarize_and_trim(key)

    # Write-through to SQLite
    try:
        with _db_ctx() as conn:
            conn.execute(
                "INSERT INTO conversations (bot_name, user_id, role, content, topic_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (system_key, user_id, role, content, topic_id, now),
            )
    except Exception as e:
        logger.warning(f"Failed to persist message for {system_key}:{user_id}: {e}")


# Number of recent messages to keep verbatim (rest gets summarized)
_KEEP_RECENT = 8
# Summary marker prefix
_SUMMARY_MARKER = "[Context summary from earlier conversation]"


def _summarize_and_trim(key: tuple):
    """Summarize older messages and keep recent ones verbatim.
    Also prunes the corresponding old rows from SQLite to prevent unbounded growth.
    """
    messages = _conversations[key]
    if len(messages) <= MAX_CONVERSATION_HISTORY:
        return

    # Split into older (to summarize) and recent (to keep)
    older = messages[:-_KEEP_RECENT]
    recent = messages[-_KEEP_RECENT:]

    # Check if first message is already a summary
    if older and older[0]["content"].startswith(_SUMMARY_MARKER):
        existing_summary = older[0]["content"]
        older = older[1:]  # Don't re-summarize the summary
    else:
        existing_summary = ""

    # Build a text summary of older messages (lightweight, no LLM call)
    summary_parts = []
    if existing_summary:
        summary_parts.append(existing_summary.replace(_SUMMARY_MARKER + " ", ""))

    for msg in older:
        role = "User" if msg["role"] == "user" else "Assistant"
        # Keep first 150 chars of each message
        snippet = msg["content"][:150].replace("\n", " ")
        summary_parts.append(f"{role}: {snippet}")

    summary_text = f"{_SUMMARY_MARKER} " + " | ".join(summary_parts[-10:])  # Keep last 10 snippets
    if len(summary_text) > 1500:
        summary_text = summary_text[:1500] + "..."

    # Replace conversation with summary + recent messages
    summary_msg = {
        "role": "user",
        "content": summary_text,
        "created_at": older[0].get("created_at", "") if older else "",
    }
    _conversations[key] = [summary_msg] + recent
    logger.debug(f"Summarized conversation {key}: {len(older)} older messages → 1 summary + {len(recent)} recent")

    # Prune old rows from SQLite — keep only the most recent messages
    system_key, user_id, topic_id = key
    try:
        with _db_ctx() as conn:
            # Keep only the N most recent rows for this user/system/topic
            conn.execute(
                "DELETE FROM conversations WHERE bot_name = ? AND user_id = ? "
                "AND COALESCE(topic_id, '') = ? AND id NOT IN ("
                "  SELECT id FROM conversations WHERE bot_name = ? AND user_id = ? "
                "  AND COALESCE(topic_id, '') = ? ORDER BY created_at DESC LIMIT ?"
                ")",
                (system_key, user_id, topic_id, system_key, user_id, topic_id, _KEEP_RECENT),
            )
    except Exception as e:
        logger.debug(f"Failed to prune SQLite conversations for {key}: {e}")


def clear_history(system_key: str, user_id: str, topic_id: str = ""):
    """Clear conversation history for a specific user and system."""
    key = (system_key, user_id, topic_id)
    _conversations.pop(key, None)
    _hydrated.discard(key)

    try:
        with _db_ctx() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE bot_name = ? AND user_id = ? AND COALESCE(topic_id, '') = ?",
                (system_key, user_id, topic_id),
            )
    except Exception as e:
        logger.warning(f"Failed to clear persisted history: {e}")

    logger.info(f"Cleared history for {system_key}:{user_id}:{topic_id}")


def clear_all():
    """Clear all conversation histories."""
    _conversations.clear()
    _hydrated.clear()

    try:
        with _db_ctx() as conn:
            conn.execute("DELETE FROM conversations")
    except Exception as e:
        logger.warning(f"Failed to clear all persisted conversations: {e}")


def get_cross_system_context(
    user_id: str,
    system_keys: list[str],
    exclude_system: str = None,
) -> list[dict]:
    """
    Get recent conversation context from other systems for cross-system awareness.

    Args:
        user_id: User identifier
        system_keys: List of all system keys to check
        exclude_system: System to exclude (the currently active one)

    Returns:
        List of the most recent messages from other systems.
    """
    cross_context = []
    for sys_key in system_keys:
        if sys_key == exclude_system:
            continue
        history = get_history(sys_key, user_id)
        if history:
            recent = history[-2:]
            for msg in recent:
                cross_context.append(
                    {
                        "role": msg["role"],
                        "content": f"[From {sys_key}] {msg['content'][:500]}",
                    }
                )
    return cross_context


def get_history_with_timestamps(system_key: str, user_id: str, topic_id: str = "") -> list[dict]:
    """Get conversation history with timestamp prefixes for temporal awareness."""
    _hydrate_if_needed(system_key, user_id, topic_id)
    key = (system_key, user_id, topic_id)
    result = []
    for msg in _conversations.get(key, []):
        ts = msg.get("created_at", "")
        content = msg["content"]
        if ts:
            content = f"[{ts}] {content}"
        result.append({"role": msg["role"], "content": content})
    return result


def get_last_assistant_message(system_key: str, user_id: str) -> str | None:
    """Get the most recent assistant message for a user in a system."""
    history = get_history(system_key, user_id)
    for msg in reversed(history):
        if msg["role"] == "assistant":
            return msg["content"]
    return None
