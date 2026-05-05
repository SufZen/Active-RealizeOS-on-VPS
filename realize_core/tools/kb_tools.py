"""
Knowledge Base tools — read and write KB files for persistent learning and on-demand navigation.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


async def kb_append(file_path: str, content: str, kb_path: str = None) -> dict:
    """
    Append content to a KB file within the systems/ directory.

    Args:
        file_path: Relative path within KB (must start with "systems/").
        content: Content to append.
        kb_path: Base KB path (auto-detected from config if not provided).

    Returns:
        dict with status, file, and bytes_written.
    """
    # Resolve KB base path
    if kb_path:
        base = Path(kb_path)
    else:
        from realize_core.config import KB_PATH

        base = KB_PATH

    # Security: validate path stays within systems/
    clean_path = Path(file_path)
    if ".." in clean_path.parts:
        return {"status": "error", "error": "Path traversal not allowed"}
    if clean_path.parts[0] != "systems" if clean_path.parts else True:
        return {"status": "error", "error": "Path must start with 'systems/'"}

    full_path = base / clean_path

    # Resolve and verify containment (prevents symlink/.. bypass)
    resolved = full_path.resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved) + os.sep) and resolved != base_resolved:
        return {"status": "error", "error": "Path escapes KB directory"}

    full_path.parent.mkdir(parents=True, exist_ok=True)

    separator = "\n\n---\n\n"
    entry = f"{separator}{content}\n"

    try:
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(entry)
        bytes_written = len(entry.encode("utf-8"))
        logger.info(f"kb_append: wrote {bytes_written} bytes to {full_path}")
        return {"status": "ok", "file": str(clean_path), "bytes_written": bytes_written}
    except Exception as e:
        logger.error(f"kb_append failed: {e}")
        return {"status": "error", "error": str(e)}


def _validate_kb_path(file_path: str, base: Path) -> tuple[Path | None, dict | None]:
    """
    Validate and resolve a KB file path to prevent traversal attacks.
    Returns (resolved_path, None) on success or (None, error_dict) on failure.
    """
    clean_path = Path(file_path)
    if ".." in clean_path.parts:
        return None, {"status": "error", "error": "Path traversal not allowed"}

    full_path = base / clean_path
    resolved = full_path.resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved) + os.sep) and resolved != base_resolved:
        return None, {"status": "error", "error": "Path escapes KB directory"}

    return resolved, None


async def kb_get(file_path: str, max_chars: int = 6000, kb_path: str = None) -> dict:
    """
    Read the full content of a single KB file.

    Args:
        file_path: Relative path within the KB (e.g. 'systems/realization/B-brain/domain-knowledge.md').
        max_chars: Maximum characters to return (default 6000, ~1500 tokens).
        kb_path: Base KB path (auto-detected from config if not provided).

    Returns:
        dict with status, path, content, and truncated flag.
    """
    if kb_path:
        base = Path(kb_path)
    else:
        from realize_core.config import KB_PATH

        base = KB_PATH

    resolved, err = _validate_kb_path(file_path, base)
    if err:
        return err

    if not resolved.exists():
        return {"status": "error", "error": f"File not found: {file_path}"}

    try:
        content = resolved.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = resolved.read_text(encoding="latin-1")
        except Exception as e:
            return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

    truncated = len(content) > max_chars
    return {
        "status": "ok",
        "path": file_path,
        "content": content[:max_chars],
        "truncated": truncated,
        "total_chars": len(content),
    }


async def kb_search(
    query: str,
    system_key: str = None,
    top_k: int = 8,
    layer: str = None,
    kb_path: str = None,
) -> dict:
    """
    Search the KB index for files relevant to a query.
    Returns paths and summaries only — use kb_get to read full content.

    Args:
        query: Search query string.
        system_key: Filter by venture system key (optional).
        top_k: Number of results to return (default 8).
        layer: Filter by FABRIC layer F/A/B/R/I/C/shared/skill (optional).
        kb_path: Base KB path (auto-detected from config if not provided).

    Returns:
        dict with status and results list [{path, title, system_key, summary, score}].
    """
    try:
        from realize_core.kb.indexer import list_resources, semantic_search

        if kb_path:
            from realize_core.config import KB_PATH

            db_path = Path(kb_path) / "kb_index.db"
        else:
            from realize_core.config import KB_PATH

            db_path = KB_PATH / "kb_index.db"

        # Run semantic search for scored results
        raw = semantic_search(query, system_key=system_key, top_k=top_k, db_path=db_path)

        # Enrich with summaries from the resource manifest
        manifest = {r["path"]: r for r in list_resources(system_key=system_key, layer=layer, db_path=db_path)}

        results = []
        for r in raw:
            path = r["path"]
            # Apply layer filter if requested
            if layer and manifest.get(path, {}).get("layer") != layer:
                continue
            summary = manifest.get(path, {}).get("summary", r.get("snippet", "")[:200])
            results.append(
                {
                    "path": path,
                    "title": r.get("title", ""),
                    "system_key": r.get("system_key", ""),
                    "summary": summary,
                    "score": round(r.get("score", 0.0), 3),
                }
            )
            if len(results) >= top_k:
                break

        return {"status": "ok", "query": query, "results": results}
    except Exception as e:
        logger.error(f"kb_search failed: {e}")
        return {"status": "error", "error": str(e)}


async def kb_outline(
    system_key: str = None,
    layer: str = None,
    kind: str = None,
    kb_path: str = None,
) -> dict:
    """
    Return a manifest table of contents for a venture system or the whole KB.
    Use this to discover what files exist before deciding what to read.

    Args:
        system_key: Filter by venture system key (optional — omit for all systems).
        layer: Filter by FABRIC layer F/A/B/R/I/C/shared/skill (optional).
        kind: Filter by resource kind md/agent/skill_yaml (optional).
        kb_path: Base KB path (auto-detected from config if not provided).

    Returns:
        dict with status and resources list [{path, title, layer, kind, summary, tokens}].
    """
    try:
        from realize_core.kb.indexer import list_resources

        if kb_path:
            db_path = Path(kb_path) / "kb_index.db"
        else:
            from realize_core.config import KB_PATH

            db_path = KB_PATH / "kb_index.db"

        resources = list_resources(system_key=system_key, layer=layer, kind=kind, db_path=db_path)
        return {
            "status": "ok",
            "system_key": system_key,
            "layer": layer,
            "kind": kind,
            "count": len(resources),
            "resources": resources,
        }
    except Exception as e:
        logger.error(f"kb_outline failed: {e}")
        return {"status": "error", "error": str(e)}


TOOL_FUNCTIONS = {
    "kb_append": kb_append,
    "kb_get": kb_get,
    "kb_search": kb_search,
    "kb_outline": kb_outline,
}
KB_READ_TOOLS = {"kb_get", "kb_search", "kb_outline"}
KB_WRITE_TOOLS = {"kb_append"}
