"""
Knowledge Base Indexer: Indexes markdown files for hybrid search.

Combines FTS5 keyword search with vector embeddings for semantic matching.
Hybrid scoring: 0.7 * vector_similarity + 0.3 * keyword_rank (BM25).
Uses fastembed for local-only embeddings (no API calls, no data leaving the machine).
Falls back to FTS5-only search when fastembed is not installed.

Index stored in SQLite for persistence across restarts.

Tables:
  kb_files    — full content + embeddings for semantic search (markdown only)
  kb_fts      — FTS5 virtual table over kb_files
  kb_resources — lightweight manifest: path, title, layer, kind, summary, tokens
                 Covers markdown + skill YAMLs; used by agents as a ToC.
"""

import json
import logging
import sqlite3
import struct
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Embedding model (lazy-loaded)
_embedder = None
_embedder_available = None

# FABRIC layer order for sorting
_LAYER_ORDER = {"F": 0, "A": 1, "B": 2, "R": 3, "I": 4, "C": 5, "shared": 6, "skill": 7}


def _get_conn(db_path: Path) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and performance PRAGMAs."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-8000")
    return conn


def _init_index_db(db_path: Path):
    """Create the index tables."""
    conn = _get_conn(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kb_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            title TEXT,
            system_key TEXT,
            content TEXT,
            embedding BLOB,
            file_mtime REAL DEFAULT 0,
            last_indexed TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts
        USING fts5(path, title, content, system_key, content='kb_files', content_rowid='id')
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS kb_ai AFTER INSERT ON kb_files BEGIN
            INSERT INTO kb_fts(rowid, path, title, content, system_key)
            VALUES (new.id, new.path, new.title, new.content, new.system_key);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS kb_ad AFTER DELETE ON kb_files BEGIN
            INSERT INTO kb_fts(kb_fts, rowid, path, title, content, system_key)
            VALUES ('delete', old.id, old.path, old.title, old.content, old.system_key);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS kb_au AFTER UPDATE ON kb_files BEGIN
            INSERT INTO kb_fts(kb_fts, rowid, path, title, content, system_key)
            VALUES ('delete', old.id, old.path, old.title, old.content, old.system_key);
            INSERT INTO kb_fts(rowid, path, title, content, system_key)
            VALUES (new.id, new.path, new.title, new.content, new.system_key);
        END
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_system_key ON kb_files(system_key)")

    # Manifest table — lightweight resource registry (markdown + skill YAMLs)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kb_resources (
            path TEXT PRIMARY KEY,
            title TEXT,
            system_key TEXT,
            layer TEXT,
            kind TEXT,
            tags TEXT,
            summary TEXT,
            tokens INTEGER,
            frontmatter_used INTEGER DEFAULT 0,
            file_mtime REAL DEFAULT 0,
            last_indexed TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_res_system ON kb_resources(system_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_res_layer ON kb_resources(layer)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_res_kind ON kb_resources(kind)")

    conn.commit()
    conn.close()


def _get_embedder():
    """Get the fastembed embedding model (lazy-loaded, optional)."""
    global _embedder, _embedder_available
    if _embedder_available is False:
        return None
    if _embedder is not None:
        return _embedder
    try:
        from fastembed import TextEmbedding

        _embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        _embedder_available = True
        logger.info("Fastembed loaded: BAAI/bge-small-en-v1.5 (local embeddings active)")
        return _embedder
    except ImportError:
        _embedder_available = False
        logger.info("Fastembed not installed — FTS5-only search (pip install fastembed for hybrid)")
        return None
    except Exception as e:
        _embedder_available = False
        logger.warning(f"Fastembed failed to load: {e} — FTS5-only search")
        return None


def _embed_text(text: str) -> bytes | None:
    """Embed text and return as bytes (for SQLite BLOB storage)."""
    embedder = _get_embedder()
    if embedder is None:
        return None
    try:
        embeddings = list(embedder.embed([text[:2000]]))
        vec = embeddings[0]
        return struct.pack(f"{len(vec)}f", *vec)
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def _bytes_to_vec(data: bytes) -> list[float]:
    """Convert BLOB bytes back to a float vector."""
    count = len(data) // 4
    return list(struct.unpack(f"{count}f", data))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _detect_system(path: str, systems_config: dict = None) -> str:
    """Detect which system a file belongs to from its path."""
    path_lower = path.lower()
    if systems_config:
        for key, conf in systems_config.items():
            sys_dir = conf.get("system_dir", "").lower()
            if sys_dir and sys_dir in path_lower:
                return key
    # Default: extract from path structure (systems/<key>/...)
    parts = Path(path).parts
    if len(parts) >= 2 and parts[0] == "systems":
        return parts[1]
    return "shared"


def _extract_title(content: str, path: str) -> str:
    """Extract the first heading from markdown content, or use filename."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return Path(path).stem.replace("-", " ").title()


def _build_search_dirs(kb_path: Path) -> list[str]:
    """
    Auto-discover FABRIC directories to index from all systems.
    No hardcoded paths — scans the systems/ directory dynamically.
    Includes C-creations alongside the original F/A/B/R/I set.
    """
    dirs = []
    systems_dir = kb_path / "systems"
    if systems_dir.exists():
        for system_dir in systems_dir.iterdir():
            if system_dir.is_dir() and not system_dir.name.startswith("."):
                for fabric_dir in ["F-foundations", "A-agents", "B-brain", "R-routines", "I-insights", "C-creations"]:
                    subdir = system_dir / fabric_dir
                    if subdir.exists():
                        dirs.append(str(subdir.relative_to(kb_path)))

    # Also index shared/ directory
    shared_dir = kb_path / "shared"
    if shared_dir.exists():
        dirs.append("shared")

    return dirs


def _build_skill_yaml_paths(kb_path: Path) -> list[Path]:
    """Collect all skill YAML files under R-routines/skills/ across all systems."""
    yamls = []
    systems_dir = kb_path / "systems"
    if not systems_dir.exists():
        return yamls
    for system_dir in systems_dir.iterdir():
        if not system_dir.is_dir() or system_dir.name.startswith("."):
            continue
        skills_dir = system_dir / "R-routines" / "skills"
        if skills_dir.exists():
            yamls.extend(skills_dir.glob("*.yaml"))
    return yamls


def _classify_layer(rel_path: str) -> str:
    """Classify a resource into a FABRIC layer letter (or 'shared'/'skill')."""
    parts = Path(rel_path).parts
    # skill yamls get their own kind
    if rel_path.endswith(".yaml"):
        return "skill"
    # systems/<key>/<FABRIC-dir>/...
    if len(parts) >= 3 and parts[0] == "systems":
        fabric = parts[2]
        prefix = fabric[0].upper() if fabric else ""
        if prefix in ("F", "A", "B", "R", "I", "C"):
            return prefix
    # shared/ top-level content
    if parts[0] == "shared":
        return "shared"
    return "B"  # default fallback


def _classify_kind(rel_path: str) -> str:
    """Classify resource kind from its path."""
    p = Path(rel_path)
    if p.suffix == ".yaml":
        return "skill_yaml"
    parts = p.parts
    if len(parts) >= 3 and parts[0] == "systems" and parts[2] == "A-agents":
        return "agent"
    return "md"


def _extract_frontmatter(content: str) -> dict:
    """Parse optional YAML frontmatter (--- ... ---) from file content."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    try:
        import yaml

        return yaml.safe_load(content[3:end]) or {}
    except ImportError:
        return {}
    except Exception:
        return {}


def _infer_summary_from_yaml(content: str) -> str:
    """Extract summary from skill YAML: use 'description' field."""
    try:
        import yaml

        data = yaml.safe_load(content) or {}
        desc = data.get("description", "")
        if desc:
            return str(desc)[:200]
        name = data.get("name", "")
        triggers = data.get("triggers", [])
        if triggers:
            return f"{name} — triggers: {', '.join(str(t) for t in triggers[:3])}"[:200]
        return name[:200]
    except Exception:
        return ""


def _infer_summary(content: str, path: str, frontmatter: dict, is_yaml: bool = False) -> str:
    """Derive a 1-line summary from frontmatter, then content, then filename."""
    # 1. Frontmatter summary/description
    fm_summary = frontmatter.get("summary") or frontmatter.get("description", "")
    if fm_summary:
        return str(fm_summary)[:200]

    if is_yaml:
        return _infer_summary_from_yaml(content)

    # 2. First non-heading, non-empty line of markdown
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
            return stripped[:200]

    # 3. Filename fallback
    return Path(path).stem.replace("-", " ").title()


def _cleanup_stale_entries(conn: sqlite3.Connection, seen_paths: set[str], existing_mtimes: dict) -> int:
    """Remove index entries for files that no longer exist on disk."""
    stale_paths = set(existing_mtimes.keys()) - seen_paths
    removed = 0
    for stale_path in stale_paths:
        try:
            conn.execute("DELETE FROM kb_files WHERE path = ?", (stale_path,))
            removed += 1
        except Exception as e:
            logger.debug(f"Failed to remove stale entry {stale_path}: {e}")
    if removed:
        logger.info(f"Removed {removed} stale KB index entries")
    return removed


def _cleanup_stale_resources(conn: sqlite3.Connection, seen_paths: set[str]) -> int:
    """Remove manifest entries for resources that no longer exist on disk."""
    try:
        existing = {r["path"] for r in conn.execute("SELECT path FROM kb_resources").fetchall()}
    except Exception:
        return 0
    stale = existing - seen_paths
    removed = 0
    for path in stale:
        try:
            conn.execute("DELETE FROM kb_resources WHERE path = ?", (path,))
            removed += 1
        except Exception:
            pass
    if removed:
        logger.info(f"Removed {removed} stale KB resource entries")
    return removed


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a query string for FTS5 MATCH to prevent OperationalError."""
    # Remove FTS5 special operators that could cause parse errors
    sanitized = query.replace('"', "").replace("*", "").replace("(", "").replace(")", "")
    # Collapse boolean operators that would confuse FTS5
    words = sanitized.split()
    words = [w for w in words if w.upper() not in ("AND", "OR", "NOT", "NEAR")]
    return " ".join(words).strip()


def _upsert_resource(
    conn: sqlite3.Connection,
    rel_path: str,
    title: str,
    system_key: str,
    summary: str,
    tags: list,
    tokens: int,
    frontmatter_used: bool,
    file_mtime: float,
    now: str,
):
    """Upsert a row into kb_resources."""
    layer = _classify_layer(rel_path)
    kind = _classify_kind(rel_path)
    tags_json = json.dumps(tags)
    try:
        conn.execute(
            """
            INSERT INTO kb_resources
                (path, title, system_key, layer, kind, tags, summary, tokens, frontmatter_used, file_mtime, last_indexed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                title=excluded.title, system_key=excluded.system_key,
                layer=excluded.layer, kind=excluded.kind, tags=excluded.tags,
                summary=excluded.summary, tokens=excluded.tokens,
                frontmatter_used=excluded.frontmatter_used,
                file_mtime=excluded.file_mtime, last_indexed=excluded.last_indexed
            """,
            (
                rel_path,
                title,
                system_key,
                layer,
                kind,
                tags_json,
                summary,
                tokens,
                int(frontmatter_used),
                file_mtime,
                now,
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to upsert resource {rel_path}: {e}")


def index_kb_files(kb_root: str, db_path: Path = None, force: bool = False) -> int:
    """
    Walk all .md files in KB directories, index their content and embeddings.
    Also indexes skill YAMLs into the kb_resources manifest (without embeddings).
    Uses incremental indexing — only re-indexes files whose mtime changed.

    Args:
        kb_root: Root path of the knowledge base
        db_path: Path for the index database. Defaults to <kb_root>/kb_index.db
        force: If True, re-index all files regardless of mtime

    Returns:
        Number of files indexed.
    """
    kb_path = Path(kb_root)
    if db_path is None:
        db_path = kb_path / "kb_index.db"

    _init_index_db(db_path)
    conn = _get_conn(db_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0

    try:
        # Load existing mtimes for incremental check
        existing_mtimes = {}
        if not force:
            try:
                rows = conn.execute("SELECT path, file_mtime FROM kb_files").fetchall()
                existing_mtimes = {r["path"]: r["file_mtime"] or 0 for r in rows}
            except Exception:
                pass

        # Also load existing resource mtimes for incremental check
        existing_resource_mtimes = {}
        if not force:
            try:
                rows = conn.execute("SELECT path, file_mtime FROM kb_resources").fetchall()
                existing_resource_mtimes = {r["path"]: r["file_mtime"] or 0 for r in rows}
            except Exception:
                pass

        # Auto-discover directories to index
        search_dirs = _build_search_dirs(kb_path)

        file_data = []
        skipped = 0
        seen_paths: set[str] = set()

        for search_dir in search_dirs:
            dir_path = kb_path / search_dir
            if not dir_path.exists():
                continue

            for md_file in dir_path.rglob("*.md"):
                try:
                    rel_path = str(md_file.relative_to(kb_path))
                    seen_paths.add(rel_path)
                    current_mtime = md_file.stat().st_mtime

                    if not force and rel_path in existing_mtimes:
                        if current_mtime < existing_mtimes[rel_path]:
                            skipped += 1
                            continue

                    try:
                        content = md_file.read_text(encoding="utf-8-sig")
                    except UnicodeDecodeError:
                        try:
                            content = md_file.read_text(encoding="latin-1")
                        except Exception:
                            logger.warning(f"Skipping {md_file}: unsupported encoding")
                            continue
                    title = _extract_title(content, rel_path)
                    system_key = _detect_system(rel_path)
                    indexed_content = content[:5000]
                    file_data.append((rel_path, title, system_key, indexed_content, current_mtime, content))
                except Exception as e:
                    logger.warning(f"Failed to read {md_file}: {e}")

        if not file_data:
            # Still clean up stale entries even if no files changed
            _cleanup_stale_entries(conn, seen_paths, existing_mtimes)
            _cleanup_stale_resources(conn, seen_paths)
            conn.commit()
            logger.info(f"KB index: 0 files changed ({skipped} unchanged)")
            # Still process skill YAMLs (they don't go into kb_files)
        else:
            # Batch embed if available
            embedder = _get_embedder()
            embeddings_map = {}
            if embedder and file_data:
                try:
                    texts = [f"{title} {content[:2000]}" for _, title, _, content, _, _ in file_data]
                    vectors = list(embedder.embed(texts))
                    for i, (rel_path, _, _, _, _, _) in enumerate(file_data):
                        vec = vectors[i]
                        embeddings_map[rel_path] = struct.pack(f"{len(vec)}f", *vec)
                    logger.info(f"Generated embeddings for {len(vectors)} files")
                except Exception as e:
                    logger.warning(f"Batch embedding failed: {e}")

            # Upsert changed files
            for rel_path, title, system_key, indexed_content, file_mtime, full_content in file_data:
                try:
                    embedding_blob = embeddings_map.get(rel_path)
                    existing = conn.execute("SELECT id FROM kb_files WHERE path = ?", (rel_path,)).fetchone()
                    if existing:
                        if embedding_blob:
                            conn.execute(
                                "UPDATE kb_files SET title=?, content=?, system_key=?, embedding=?, file_mtime=?, last_indexed=? WHERE path=?",
                                (title, indexed_content, system_key, embedding_blob, file_mtime, now, rel_path),
                            )
                        else:
                            conn.execute(
                                "UPDATE kb_files SET title=?, content=?, system_key=?, file_mtime=?, last_indexed=? WHERE path=?",
                                (title, indexed_content, system_key, file_mtime, now, rel_path),
                            )
                    else:
                        conn.execute(
                            "INSERT INTO kb_files (path, title, system_key, content, embedding, file_mtime, last_indexed) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (rel_path, title, system_key, indexed_content, embedding_blob, file_mtime, now),
                        )
                    count += 1

                    # Update resource manifest for this markdown file
                    frontmatter = _extract_frontmatter(full_content)
                    summary = _infer_summary(full_content, rel_path, frontmatter)
                    tags = frontmatter.get("tags", [])
                    if isinstance(tags, str):
                        tags = [tags]
                    tokens = len(full_content) // 4
                    _upsert_resource(
                        conn,
                        rel_path,
                        title,
                        system_key,
                        summary,
                        tags,
                        tokens,
                        bool(frontmatter),
                        file_mtime,
                        now,
                    )
                except Exception as e:
                    logger.warning(f"Failed to index {rel_path}: {e}")

            # Clean up entries for files that no longer exist on disk
            _cleanup_stale_entries(conn, seen_paths, existing_mtimes)

        # ----------------------------------------------------------------
        # Index skill YAMLs into kb_resources (no embedding, no kb_files)
        # ----------------------------------------------------------------
        yaml_files = _build_skill_yaml_paths(kb_path)
        yaml_count = 0
        for yaml_file in yaml_files:
            try:
                rel_path = str(yaml_file.relative_to(kb_path))
                seen_paths.add(rel_path)
                current_mtime = yaml_file.stat().st_mtime

                if not force and rel_path in existing_resource_mtimes:
                    if current_mtime <= existing_resource_mtimes[rel_path]:
                        continue

                try:
                    content = yaml_file.read_text(encoding="utf-8-sig")
                except UnicodeDecodeError:
                    content = yaml_file.read_text(encoding="latin-1")

                system_key = _detect_system(rel_path)
                summary = _infer_summary(content, rel_path, {}, is_yaml=True)
                # Extract title from YAML name field
                title = rel_path
                try:
                    import yaml as _yaml

                    data = _yaml.safe_load(content) or {}
                    title = data.get("name", Path(rel_path).stem.replace("-", " ").title())
                except Exception:
                    title = Path(rel_path).stem.replace("-", " ").title()

                tokens = len(content) // 4
                _upsert_resource(
                    conn,
                    rel_path,
                    title,
                    system_key,
                    summary,
                    [],
                    tokens,
                    False,
                    current_mtime,
                    now,
                )
                yaml_count += 1
            except Exception as e:
                logger.warning(f"Failed to index YAML {yaml_file}: {e}")

        _cleanup_stale_resources(conn, seen_paths)
        conn.commit()
        mode = "hybrid (vector+keyword)" if (file_data and any(embeddings_map for _ in [1])) else "keyword-only (FTS5)"
        logger.info(f"Indexed {count} KB files + {yaml_count} skill YAMLs ({skipped} unchanged) [{mode}]")
    finally:
        conn.close()
    return count + yaml_count


def semantic_search(
    query: str,
    system_key: str = None,
    top_k: int = 5,
    db_path: Path = None,
    kb_root: str = None,
) -> list[dict]:
    """
    Hybrid search: combines vector similarity (0.7) with FTS5 keyword rank (0.3).

    Args:
        query: Search query
        system_key: Filter by system (optional)
        top_k: Maximum results
        db_path: Path to index database
        kb_root: KB root for default db_path

    Returns:
        List of dicts with path, title, system_key, snippet, score.
    """
    if db_path is None:
        from realize_core.config import KB_PATH

        db_path = KB_PATH / "kb_index.db"

    _init_index_db(db_path)
    conn = _get_conn(db_path)

    fts_results = _fts_search(conn, query, system_key, top_k=top_k * 2)
    query_embedding = _embed_text(query)

    if query_embedding is not None:
        vector_results = _vector_search(conn, query_embedding, system_key, top_k=top_k * 2)
        results = _merge_hybrid(fts_results, vector_results, top_k)
        conn.close()
        return results

    conn.close()
    return fts_results[:top_k]


def list_resources(
    system_key: str = None,
    layer: str = None,
    kind: str = None,
    limit: int = 200,
    db_path: Path = None,
) -> list[dict]:
    """
    Return manifest rows from kb_resources, optionally filtered and sorted by FABRIC layer.

    Args:
        system_key: Filter by system key (optional)
        layer: Filter by layer letter F/A/B/R/I/C/shared/skill (optional)
        kind: Filter by kind md/agent/skill_yaml (optional)
        limit: Max rows to return
        db_path: Path to index database

    Returns:
        List of dicts with path, title, system_key, layer, kind, summary, tokens.
    """
    if db_path is None:
        from realize_core.config import KB_PATH

        db_path = KB_PATH / "kb_index.db"

    _init_index_db(db_path)
    conn = _get_conn(db_path)

    try:
        conditions = []
        params: list = []
        if system_key:
            conditions.append("system_key = ?")
            params.append(system_key)
        if layer:
            conditions.append("layer = ?")
            params.append(layer)
        if kind:
            conditions.append("kind = ?")
            params.append(kind)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        rows = conn.execute(
            f"SELECT path, title, system_key, layer, kind, summary, tokens, tags FROM kb_resources {where} ORDER BY layer, title LIMIT ?",
            params,
        ).fetchall()

        results = []
        for r in rows:
            results.append(
                {
                    "path": r["path"],
                    "title": r["title"],
                    "system_key": r["system_key"],
                    "layer": r["layer"],
                    "kind": r["kind"],
                    "summary": r["summary"],
                    "tokens": r["tokens"],
                    "tags": json.loads(r["tags"] or "[]"),
                }
            )
        # Sort by FABRIC layer order
        results.sort(key=lambda x: (_LAYER_ORDER.get(x["layer"], 99), x["title"] or ""))
        return results
    except Exception as e:
        logger.warning(f"list_resources failed: {e}")
        return []
    finally:
        conn.close()


def get_resource(path: str, db_path: Path = None) -> dict | None:
    """
    Return a single manifest row for a given path.

    Args:
        path: Relative path within the KB
        db_path: Path to index database

    Returns:
        Dict with resource metadata, or None if not found.
    """
    if db_path is None:
        from realize_core.config import KB_PATH

        db_path = KB_PATH / "kb_index.db"

    _init_index_db(db_path)
    conn = _get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT path, title, system_key, layer, kind, summary, tokens, tags FROM kb_resources WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None:
            return None
        return {
            "path": row["path"],
            "title": row["title"],
            "system_key": row["system_key"],
            "layer": row["layer"],
            "kind": row["kind"],
            "summary": row["summary"],
            "tokens": row["tokens"],
            "tags": json.loads(row["tags"] or "[]"),
        }
    except Exception as e:
        logger.warning(f"get_resource failed: {e}")
        return None
    finally:
        conn.close()


def _fts_search(conn, query: str, system_key: str = None, top_k: int = 10) -> list[dict]:
    """FTS5 keyword search with BM25 ranking."""
    try:
        safe_query = _sanitize_fts_query(query)
        if not safe_query:
            return []
        if system_key:
            rows = conn.execute(
                "SELECT path, title, system_key, snippet(kb_fts, 2, '>>>', '<<<', '...', 50) as snippet, rank "
                "FROM kb_fts WHERE kb_fts MATCH ? AND system_key = ? ORDER BY rank LIMIT ?",
                (safe_query, system_key, top_k),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT path, title, system_key, snippet(kb_fts, 2, '>>>', '<<<', '...', 50) as snippet, rank "
                "FROM kb_fts WHERE kb_fts MATCH ? ORDER BY rank LIMIT ?",
                (safe_query, top_k),
            ).fetchall()

        results = []
        if rows:
            min_rank = min(r["rank"] for r in rows)
            max_rank = max(r["rank"] for r in rows)
            rank_range = max_rank - min_rank if max_rank != min_rank else 1.0
            for row in rows:
                norm_score = 1.0 - ((row["rank"] - min_rank) / rank_range) if rank_range else 1.0
                results.append(
                    {
                        "path": row["path"],
                        "title": row["title"],
                        "system_key": row["system_key"],
                        "snippet": row["snippet"],
                        "keyword_score": norm_score,
                    }
                )
        return results

    except sqlite3.OperationalError:
        sql = "SELECT path, title, system_key, substr(content, 1, 200) as snippet FROM kb_files WHERE content LIKE ? OR title LIKE ?"
        params = [f"%{query}%", f"%{query}%"]
        if system_key:
            sql += " AND system_key = ?"
            params.append(system_key)
        sql += " LIMIT ?"
        params.append(top_k)
        rows = conn.execute(sql, params).fetchall()
        return [{**dict(row), "keyword_score": 0.5} for row in rows]


def _vector_search(conn, query_blob: bytes, system_key: str = None, top_k: int = 10) -> list[dict]:
    """Vector similarity search using stored embeddings."""
    query_vec = _bytes_to_vec(query_blob)

    sql = "SELECT path, title, system_key, embedding, substr(content, 1, 200) as snippet FROM kb_files WHERE embedding IS NOT NULL"
    params = []
    if system_key:
        sql += " AND system_key = ?"
        params.append(system_key)
    rows = conn.execute(sql, params).fetchall()

    scored = []
    for row in rows:
        if row["embedding"]:
            doc_vec = _bytes_to_vec(row["embedding"])
            sim = _cosine_similarity(query_vec, doc_vec)
            scored.append(
                {
                    "path": row["path"],
                    "title": row["title"],
                    "system_key": row["system_key"],
                    "snippet": row["snippet"],
                    "vector_score": sim,
                }
            )

    scored.sort(key=lambda x: x["vector_score"], reverse=True)
    return scored[:top_k]


def _merge_hybrid(
    fts_results: list[dict],
    vector_results: list[dict],
    top_k: int,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> list[dict]:
    """Merge FTS5 and vector results with weighted scoring."""
    merged: dict[str, dict] = {}

    for r in fts_results:
        path = r["path"]
        merged[path] = {**r, "vector_score": 0.0}

    for r in vector_results:
        path = r["path"]
        if path in merged:
            merged[path]["vector_score"] = r.get("vector_score", 0.0)
        else:
            merged[path] = {**r, "keyword_score": 0.0}

    for entry in merged.values():
        entry["score"] = vector_weight * entry.get("vector_score", 0.0) + keyword_weight * entry.get(
            "keyword_score", 0.0
        )

    results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)

    for r in results:
        r.pop("keyword_score", None)
        r.pop("vector_score", None)

    return results[:top_k]
