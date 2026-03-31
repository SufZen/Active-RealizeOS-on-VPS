"""
Persistent Memory Store for RealizeOS (SQLite).

Stores memories, conversations, sessions, episodes, and LLM usage as searchable records.
Schema: memories(id, system_key, category, content, tags, created_at)
Categories: feedback | decision | learning | preference | entity
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Database path — configurable
DB_PATH: Path | None = None


def _resolve_db_path() -> Path:
    """Resolve the database path from config or default."""
    global DB_PATH
    if DB_PATH is None:
        from realize_core.config import DATA_PATH

        DB_PATH = DATA_PATH / "memory.db"
    return DB_PATH


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with row factory and performance PRAGMAs."""
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-8000")
    return conn


@contextmanager
def db_connection():
    """Context manager for safe SQLite connections with auto-commit/rollback/close."""
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the memory database and create tables if needed."""
    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_key TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, system_key, category, content='memories', content_rowid='id')
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, system_key, category)
                VALUES (new.id, new.content, new.system_key, new.category);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, system_key, category)
                VALUES ('delete', old.id, old.content, old.system_key, old.category);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, system_key, category)
                VALUES ('delete', old.id, old.content, old.system_key, old.category);
                INSERT INTO memories_fts(rowid, content, system_key, category)
                VALUES (new.id, new.content, new.system_key, new.category);
            END
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                topic_id TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_lookup
            ON conversations(bot_name, user_id, created_at)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                system_key TEXT NOT NULL,
                user_id TEXT NOT NULL,
                brief TEXT NOT NULL,
                task_type TEXT NOT NULL,
                active_agent TEXT NOT NULL,
                stage TEXT NOT NULL,
                pipeline TEXT NOT NULL,
                pipeline_index INTEGER DEFAULT 0,
                context_files TEXT DEFAULT '[]',
                drafts TEXT DEFAULT '[]',
                review TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(system_key, user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                tenant_id TEXT DEFAULT 'default',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interaction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT,
                feedback_signal TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                system_key TEXT NOT NULL,
                user_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT DEFAULT '',
                steps_executed INTEGER DEFAULT 0,
                steps_failed INTEGER DEFAULT 0,
                outcome TEXT DEFAULT '',
                step_timings TEXT DEFAULT '[]'
            )
        """)
        # --- Schema migrations for existing databases ---
        # Add tenant_id to llm_usage if missing (pre-v0.1 databases)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(llm_usage)").fetchall()}
        if "tenant_id" not in cols:
            conn.execute("ALTER TABLE llm_usage ADD COLUMN tenant_id TEXT DEFAULT 'default'")
        # Add created_at to interaction_log if it only has timestamp (pre-v0.1)
        il_cols = {row[1] for row in conn.execute("PRAGMA table_info(interaction_log)").fetchall()}
        if "created_at" not in il_cols and "timestamp" in il_cols:
            conn.execute("ALTER TABLE interaction_log RENAME COLUMN timestamp TO created_at")
        elif "created_at" not in il_cols:
            conn.execute("ALTER TABLE interaction_log ADD COLUMN created_at TEXT DEFAULT ''")

        # Performance indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_system_category ON memories(system_key, category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_tenant_date ON llm_usage(tenant_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interaction_task_date ON interaction_log(task_type, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_logs_system_date ON skill_execution_logs(system_key, started_at)")

    logger.info(f"Memory database initialized at {_resolve_db_path()}")


def store_memory(system_key: str, category: str, content: str, tags: list[str] = None):
    """Store a memory record with deduplication.

    Checks for existing memories with the same system_key and category
    that have highly similar content (>80% word overlap) to prevent duplicates.
    """
    # Dedup check: look for very similar existing memories in the same scope
    # Use first few words for FTS query (more words = stricter matching via implicit AND)
    try:
        query_words = content.split()[:6]
        existing = search_memories(" ".join(query_words), system_key=system_key, limit=5)
        content_words = set(content.lower().split())
        for mem in existing:
            if mem.get("category") != category:
                continue
            existing_words = set(mem.get("content", "").lower().split())
            if not content_words or not existing_words:
                continue
            overlap = len(content_words & existing_words) / max(len(content_words), len(existing_words))
            if overlap > 0.8:
                logger.debug(f"Skipping duplicate memory (overlap={overlap:.0%}): {content[:80]}...")
                return
    except Exception:
        pass  # If dedup check fails, store anyway

    with db_connection() as conn:
        conn.execute(
            "INSERT INTO memories (system_key, category, content, tags, created_at) VALUES (?, ?, ?, ?, ?)",
            (system_key, category, content, json.dumps(tags or []), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a query string for FTS5 MATCH to prevent OperationalError."""
    sanitized = query.replace('"', "").replace("*", "").replace("(", "").replace(")", "")
    words = sanitized.split()
    words = [w for w in words if w.upper() not in ("AND", "OR", "NOT", "NEAR")]
    return " ".join(words).strip()


def search_memories(query: str, system_key: str = None, limit: int = 5) -> list[dict]:
    """Search memories using FTS5 with recency weighting.

    Results are boosted by recency: memories from the last 7 days get full weight,
    older memories decay gradually (half-life of 30 days).
    """
    safe_query = _sanitize_fts_query(query)
    if not safe_query:
        return []

    with db_connection() as conn:
        # Fetch more than needed so we can re-rank with recency
        fetch_limit = limit * 3
        if system_key:
            rows = conn.execute(
                "SELECT m.* FROM memories m JOIN memories_fts f ON m.id = f.rowid "
                "WHERE memories_fts MATCH ? AND m.system_key = ? LIMIT ?",
                (safe_query, system_key, fetch_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.* FROM memories m JOIN memories_fts f ON m.id = f.rowid WHERE memories_fts MATCH ? LIMIT ?",
                (safe_query, fetch_limit),
            ).fetchall()

    if not rows:
        return []

    # Apply recency decay: weight = 1 / (1 + days_old / 30)
    now = datetime.now()
    results = []
    for r in rows:
        record = dict(r)
        try:
            created = datetime.strptime(record["created_at"], "%Y-%m-%d %H:%M:%S")
            days_old = (now - created).days
            record["_recency_weight"] = 1.0 / (1.0 + days_old / 30.0)
        except (ValueError, KeyError):
            record["_recency_weight"] = 0.5
        results.append(record)

    # Sort by recency weight (descending) and return top N
    results.sort(key=lambda x: x["_recency_weight"], reverse=True)
    for r in results:
        r.pop("_recency_weight", None)
    return results[:limit]


def log_llm_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    tenant_id: str = "default",
):
    """Log an LLM API call for cost tracking."""
    try:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO llm_usage (model, input_tokens, output_tokens, cost_usd, tenant_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (model, input_tokens, output_tokens, cost_usd, tenant_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
    except Exception as e:
        logger.debug(f"Failed to log LLM usage: {e}")


def get_feedback_signals(task_type: str, days: int = 30) -> dict:
    """
    Get aggregated feedback signals for a task type.

    Returns:
        Dict mapping signal name to count, e.g. {"positive": 5, "negative": 2, "reset": 1}
    """
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT feedback_signal, COUNT(*) as c FROM interaction_log "
                "WHERE task_type = ? AND created_at >= ? AND feedback_signal IS NOT NULL "
                "GROUP BY feedback_signal",
                (task_type, cutoff),
            ).fetchall()
        return {row["feedback_signal"]: row["c"] for row in rows}
    except Exception:
        return {}


def get_usage_stats(tenant_id: str = "default", days: int = 30) -> dict:
    """Get usage statistics for a tenant."""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with db_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as calls, SUM(input_tokens) as inp, "
                "SUM(output_tokens) as outp, SUM(cost_usd) as cost "
                "FROM llm_usage WHERE tenant_id = ? AND created_at >= ?",
                (tenant_id, cutoff),
            ).fetchone()
        return {
            "total_calls": row["calls"] or 0,
            "total_input_tokens": row["inp"] or 0,
            "total_output_tokens": row["outp"] or 0,
            "total_cost_usd": round(row["cost"] or 0.0, 4),
        }
    except Exception:
        return {"total_calls": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_usd": 0.0}


def maintenance():
    """Run database maintenance: ANALYZE for query planner stats, VACUUM for compaction.

    Should be called periodically (e.g., daily or via `python cli.py maintain`).
    """
    try:
        with db_connection() as conn:
            conn.execute("ANALYZE")
        # VACUUM must run outside a transaction
        db_path = _resolve_db_path()
        conn = sqlite3.connect(str(db_path))
        conn.execute("VACUUM")
        conn.close()
        logger.info(f"Memory database maintenance complete: {db_path}")
    except Exception as e:
        logger.warning(f"Memory database maintenance failed: {e}")
