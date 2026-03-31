"""
Chat API routes: POST /chat, GET /conversations.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from realize_core.config import is_env_true

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    system_key: str
    user_id: str = "api-user"
    agent_key: str | None = None
    channel: str = "api"


class ChatResponse(BaseModel):
    response: str
    system_key: str
    agent_key: str
    user_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    """Send a message and get an AI response."""
    systems = request.app.state.systems
    kb_path = request.app.state.kb_path
    shared_config = request.app.state.shared_config
    features = getattr(request.app.state, "features", {})

    if body.system_key not in systems:
        available = list(systems.keys())
        raise HTTPException(
            status_code=404,
            detail=f"System '{body.system_key}' not found. Available: {available}",
        )

    system_config = systems[body.system_key]

    from realize_core.base_handler import process_message

    try:
        response = await process_message(
            system_key=body.system_key,
            user_id=body.user_id,
            message=body.message,
            kb_path=kb_path,
            system_config=system_config,
            shared_config=shared_config,
            channel=body.channel,
            agent_key=body.agent_key,
            features=features,
            all_systems=systems,
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        detail = f"Processing error: {str(e)[:200]}" if is_env_true("REALIZE_DEBUG") else "Internal processing error"
        raise HTTPException(status_code=500, detail=detail)

    # Determine which agent handled it
    from realize_core.pipeline.session import get_session

    session = get_session(body.system_key, body.user_id)
    agent_used = session.active_agent if session else (body.agent_key or "orchestrator")

    # Note: humanization is now handled by BaseChannel.handle_incoming()

    return ChatResponse(
        response=response,
        system_key=body.system_key,
        agent_key=agent_used,
        user_id=body.user_id,
    )


@router.get("/conversations/{system_key}/{user_id}")
async def get_conversations(system_key: str, user_id: str, limit: int = Query(default=50, ge=1, le=500)):
    """Get conversation history for a user in a system."""
    from realize_core.memory.conversation import get_history

    history = get_history(system_key, user_id, limit=limit)
    return {"system_key": system_key, "user_id": user_id, "messages": history}


@router.delete("/conversations/{system_key}/{user_id}")
async def clear_conversations(system_key: str, user_id: str):
    """Clear conversation history for a user."""
    from realize_core.memory.conversation import clear_history

    clear_history(system_key, user_id)
    return {"status": "cleared", "system_key": system_key, "user_id": user_id}
