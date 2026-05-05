"""
KB API routes: search, manifest, and file read access for the knowledge base.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()
logger = logging.getLogger(__name__)

_VALID_LAYERS = {"F", "A", "B", "R", "I", "C", "shared", "skill"}
_VALID_KINDS = {"md", "agent", "skill_yaml"}


def _db_path(request: Request) -> Path:
    kb_path = getattr(request.app.state, "kb_path", None)
    if kb_path:
        return Path(kb_path) / "kb_index.db"
    from realize_core.config import KB_PATH

    return KB_PATH / "kb_index.db"


@router.get("/kb/search")
async def kb_search(
    request: Request,
    q: str = Query(..., description="Search query"),
    system_key: str = Query(None, description="Filter by venture system key"),
    layer: str = Query(None, description="Filter by FABRIC layer: F/A/B/R/I/C/shared/skill"),
    top_k: int = Query(8, ge=1, le=50, description="Number of results"),
):
    """Semantic search over the KB index. Returns paths and summaries — use /kb/file to read content."""
    if layer and layer not in _VALID_LAYERS:
        raise HTTPException(status_code=400, detail=f"Invalid layer '{layer}'. Must be one of: {sorted(_VALID_LAYERS)}")
    try:
        from realize_core.kb.indexer import list_resources, semantic_search

        db = _db_path(request)
        raw = semantic_search(q, system_key=system_key, top_k=top_k, db_path=db)
        manifest = {r["path"]: r for r in list_resources(system_key=system_key, layer=layer, db_path=db)}

        results = []
        for r in raw:
            path = r["path"]
            if layer and manifest.get(path, {}).get("layer") != layer:
                continue
            summary = manifest.get(path, {}).get("summary", r.get("snippet", "")[:200])
            results.append(
                {
                    "path": path,
                    "title": r.get("title", ""),
                    "system_key": r.get("system_key", ""),
                    "layer": manifest.get(path, {}).get("layer"),
                    "summary": summary,
                    "score": round(r.get("score", 0.0), 3),
                }
            )
            if len(results) >= top_k:
                break

        return {"query": q, "count": len(results), "results": results}
    except Exception as e:
        logger.error(f"KB search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/resource")
async def get_resource(
    request: Request,
    path: str = Query(..., description="Relative path within the KB"),
):
    """Return manifest metadata for a single resource (no file content)."""
    try:
        from realize_core.kb.indexer import get_resource

        db = _db_path(request)
        resource = get_resource(path, db_path=db)
        if resource is None:
            raise HTTPException(status_code=404, detail=f"Resource '{path}' not found in index")
        return resource
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_resource failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/file")
async def get_file(
    request: Request,
    path: str = Query(..., description="Relative path within the KB"),
    max_chars: int = Query(6000, ge=100, le=50000, description="Maximum characters to return"),
):
    """Read the content of a single KB file. Path must be within systems/ or shared/."""
    import os

    kb_path = getattr(request.app.state, "kb_path", None)
    if kb_path is None:
        from realize_core.config import KB_PATH

        kb_path = KB_PATH

    kb_base = Path(kb_path).resolve()

    # Security: prevent path traversal
    clean = Path(path)
    if ".." in clean.parts:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")

    full_path = (kb_base / clean).resolve()
    if not str(full_path).startswith(str(kb_base) + os.sep) and full_path != kb_base:
        raise HTTPException(status_code=400, detail="Path escapes KB directory")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        try:
            content = full_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = full_path.read_text(encoding="latin-1")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    truncated = len(content) > max_chars
    return {
        "path": path,
        "content": content[:max_chars],
        "truncated": truncated,
        "total_chars": len(content),
    }


@router.get("/systems/{system_key}/kb/index")
async def system_kb_index(
    request: Request,
    system_key: str,
    layer: str = Query(None, description="Filter by FABRIC layer: F/A/B/R/I/C/shared/skill"),
    kind: str = Query(None, description="Filter by kind: md/agent/skill_yaml"),
):
    """Return the manifest table of contents for a venture system."""
    systems = request.app.state.systems
    if system_key not in systems:
        raise HTTPException(status_code=404, detail=f"System '{system_key}' not found")

    if layer and layer not in _VALID_LAYERS:
        raise HTTPException(status_code=400, detail=f"Invalid layer '{layer}'")
    if kind and kind not in _VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind '{kind}'")

    try:
        from realize_core.kb.indexer import list_resources

        db = _db_path(request)
        resources = list_resources(system_key=system_key, layer=layer, kind=kind, db_path=db)
        return {
            "system_key": system_key,
            "layer": layer,
            "kind": kind,
            "count": len(resources),
            "resources": resources,
        }
    except Exception as e:
        logger.error(f"system_kb_index failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
