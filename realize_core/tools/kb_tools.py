"""
Knowledge Base tools — append content to KB files for persistent learning.
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


TOOL_FUNCTIONS = {"kb_append": kb_append}
KB_READ_TOOLS = set()
KB_WRITE_TOOLS = {"kb_append"}
