"""
Webhook ingestion endpoints.

Routes inbound webhooks (ElevenLabs post-call, etc.) through the WebhookChannel.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from realize_core.config import is_env_true

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_channel(request: Request):
    """Get the webhook channel from app.state (initialized at startup)."""
    channel = getattr(request.app.state, "webhook_channel", None)
    if channel is None:
        raise HTTPException(
            status_code=503,
            detail="Webhook channel not initialized",
        )
    return channel


# NOTE: trigger-skill MUST be defined BEFORE the {endpoint_name} wildcard
# to prevent FastAPI from matching "trigger-skill" as an endpoint name.


@router.post("/webhooks/trigger-skill")
async def trigger_skill_webhook(request: Request):
    """
    Generic webhook that triggers a skill in a specific system.

    Expected JSON body:
    {
        "system_key": "realization",
        "message": "The message that triggers the skill",
        "user_id": "webhook-user"  // optional
    }

    This allows external tools (email automation, calendar, IFTTT, etc.)
    to trigger RealizeOS skills via HTTP.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    system_key = payload.get("system_key")
    message = payload.get("message")
    user_id = payload.get("user_id", "webhook-trigger")

    if not system_key or not message:
        raise HTTPException(status_code=400, detail="system_key and message are required")

    systems = request.app.state.systems
    if system_key not in systems:
        raise HTTPException(status_code=404, detail=f"System '{system_key}' not found")

    kb_path = request.app.state.kb_path
    shared_config = request.app.state.shared_config
    system_config = systems[system_key]
    features = getattr(request.app.state, "features", {})

    from realize_core.base_handler import process_message

    try:
        response = await process_message(
            system_key=system_key,
            user_id=user_id,
            message=message,
            kb_path=kb_path,
            system_config=system_config,
            shared_config=shared_config,
            channel="webhook",
            features=features,
            all_systems=systems,
        )
    except Exception as e:
        logger.error(f"Webhook skill trigger error: {e}", exc_info=True)
        detail = str(e)[:200] if is_env_true("REALIZE_DEBUG") else "Internal processing error"
        raise HTTPException(status_code=500, detail=detail)

    return {"status": "processed", "system_key": system_key, "response": response[:500]}


@router.post("/webhooks/{endpoint_name}")
async def receive_webhook(endpoint_name: str, request: Request):
    """
    Receive an inbound webhook and route it through the engine.

    Endpoint name maps to a registered webhook in realize-os.yaml.
    Example: POST /webhooks/elevenlabs_post_call
    """
    channel = _get_channel(request)

    # Parse body
    try:
        body_bytes = await request.body()
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")

    # Get signature header (ElevenLabs uses X-ElevenLabs-Signature)
    signature = (
        request.headers.get("X-ElevenLabs-Signature", "")
        or request.headers.get("X-Hub-Signature-256", "")
        or request.headers.get("X-Signature", "")
    )

    result = await channel.process_webhook(
        endpoint_name=endpoint_name,
        payload=payload,
        body_bytes=body_bytes,
        signature=signature,
    )

    if result is None:
        # Endpoint not found or disabled or signature failed
        endpoint = channel.get_endpoint(endpoint_name)
        if endpoint is None:
            raise HTTPException(status_code=404, detail=f"Webhook endpoint '{endpoint_name}' not registered")
        raise HTTPException(status_code=403, detail="Webhook rejected (signature verification failed or endpoint disabled)")

    return {"status": "processed", "endpoint": endpoint_name}
