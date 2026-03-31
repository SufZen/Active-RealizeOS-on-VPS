"""
Evolution API routes: analytics, suggestions, and system health.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from realize_core.config import is_env_true

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RefinePromptRequest(BaseModel):
    system_key: str
    agent_key: str
    patterns: list[str]


class RefinementChange(BaseModel):
    content: str
    location: str = "end"
    type: str = "add"


class ApplyRefinementRequest(BaseModel):
    prompt_path: str
    changes: list[RefinementChange]
    system_key: str = ""
    agent_key: str = ""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _sanitized_detail(e: Exception) -> str:
    """Return error detail: full in debug mode, generic in production."""
    if is_env_true("REALIZE_DEBUG"):
        return str(e)[:300]
    return "Internal processing error"


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics/{system_key}")
async def get_analytics(system_key: str, days: int = Query(default=7, ge=1, le=365)):
    """Get interaction analytics for a system."""
    try:
        from realize_core.evolution.analytics import get_interaction_stats

        stats = get_interaction_stats(system_key=system_key, days=days)
        return {"system_key": system_key, "days": days, **stats}
    except Exception as e:
        logger.error(f"Analytics error for {system_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


@router.get("/analytics")
async def get_all_analytics(days: int = Query(default=7, ge=1, le=365)):
    """Get interaction analytics across all systems."""
    try:
        from realize_core.evolution.analytics import get_interaction_stats

        stats = get_interaction_stats(days=days)
        return {"days": days, **stats}
    except Exception as e:
        logger.error(f"Analytics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------


@router.get("/evolution/suggestions")
async def get_suggestions():
    """Get pending evolution suggestions."""
    try:
        from realize_core.evolution.gap_detector import get_pending_suggestions

        suggestions = get_pending_suggestions()
        return {"count": len(suggestions), "suggestions": suggestions}
    except Exception as e:
        logger.error(f"Suggestions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


@router.post("/evolution/run")
async def run_evolution():
    """Trigger a gap analysis run."""
    try:
        from realize_core.evolution.gap_detector import run_gap_analysis

        suggestions = await run_gap_analysis(days=7)
        return {"new_suggestions": len(suggestions), "suggestions": suggestions}
    except Exception as e:
        logger.error(f"Evolution run error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


@router.post("/evolution/approve/{suggestion_id}")
async def approve_suggestion(suggestion_id: int):
    """Approve an evolution suggestion."""
    try:
        from realize_core.evolution.gap_detector import resolve_suggestion

        resolve_suggestion(suggestion_id, status="approved")
        return {"status": "approved", "id": suggestion_id}
    except Exception as e:
        logger.error(f"Approve suggestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


@router.post("/evolution/dismiss/{suggestion_id}")
async def dismiss_suggestion(suggestion_id: int):
    """Dismiss an evolution suggestion."""
    try:
        from realize_core.evolution.gap_detector import resolve_suggestion

        resolve_suggestion(suggestion_id, status="dismissed")
        return {"status": "dismissed", "id": suggestion_id}
    except Exception as e:
        logger.error(f"Dismiss suggestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------


@router.get("/usage")
async def get_usage(days: int = Query(default=30, ge=1, le=365)):
    """Get LLM usage and cost statistics."""
    try:
        from realize_core.memory.store import get_usage_stats

        stats = get_usage_stats(days=days)
        return {"days": days, **stats}
    except Exception as e:
        logger.error(f"Usage stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


# ---------------------------------------------------------------------------
# Skill suggestion
# ---------------------------------------------------------------------------


@router.post("/evolution/suggest-skill/{suggestion_id}")
async def suggest_skill(suggestion_id: int, request: Request):
    """Generate a skill YAML from a gap detection suggestion."""
    try:
        from realize_core.evolution.gap_detector import get_pending_suggestions
        from realize_core.evolution.skill_suggester import (
            format_skill_preview,
            suggest_skill_from_gap,
        )

        suggestions = get_pending_suggestions()
        target = None
        for s in suggestions:
            if s["id"] == suggestion_id:
                target = s
                break

        if not target:
            raise HTTPException(
                status_code=404,
                detail=f"Suggestion {suggestion_id} not found or not pending",
            )

        systems = request.app.state.systems
        system_key = target.get("action_data", {}).get("system_key", "")
        system_config = systems.get(system_key, {})

        yaml_text = await suggest_skill_from_gap(target, system_config=system_config)
        if not yaml_text:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate skill suggestion",
            )

        preview = format_skill_preview(yaml_text)
        return {"suggestion_id": suggestion_id, "yaml": yaml_text, "preview": preview}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suggest skill error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


# ---------------------------------------------------------------------------
# Prompt refinement
# ---------------------------------------------------------------------------


@router.post("/evolution/refine-prompt")
async def refine_prompt(body: RefinePromptRequest, request: Request):
    """Suggest prompt improvements for an agent based on feedback patterns."""
    from realize_core.evolution.prompt_refiner import (
        format_refinement_preview,
        suggest_prompt_refinement,
    )

    systems = request.app.state.systems
    system_config = systems.get(body.system_key, {})
    kb_path = str(request.app.state.kb_path)

    try:
        result = await suggest_prompt_refinement(
            system_key=body.system_key,
            agent_key=body.agent_key,
            feedback_patterns=body.patterns,
            kb_path=kb_path,
            system_config=system_config,
        )
    except Exception as e:
        logger.error(f"Refine prompt error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))

    if not result:
        return {"message": "No prompt changes suggested"}

    preview = format_refinement_preview(result)
    return {"refinement": result, "preview": preview}


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------


@router.get("/evolution/changelog")
async def get_evolution_changelog(days: int = Query(default=30, ge=1, le=365)):
    """Get the evolution changelog (audit trail)."""
    try:
        from realize_core.evolution.engine import get_changelog

        entries = get_changelog(days=days)
        return {"days": days, "count": len(entries), "entries": entries}
    except Exception as e:
        logger.error(f"Changelog error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))


# ---------------------------------------------------------------------------
# Apply refinement
# ---------------------------------------------------------------------------


@router.post("/evolution/apply-refinement")
async def apply_refinement(body: ApplyRefinementRequest, request: Request):
    """Apply a previously suggested prompt refinement."""
    kb_path = str(request.app.state.kb_path)

    # Convert Pydantic model to dict for the underlying function
    refinement = body.model_dump()

    try:
        from realize_core.evolution.prompt_refiner import apply_prompt_refinement
        from realize_core.prompt.builder import clear_cache

        result = await apply_prompt_refinement(refinement, kb_path=kb_path)
        clear_cache()

        return {"status": "applied", "message": result}
    except Exception as e:
        logger.error(f"Apply refinement error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_sanitized_detail(e))
