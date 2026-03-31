"""
Voice Tools: ElevenLabs Conversational AI + Twilio outbound call integration.

Enables RealizeOS agents to initiate outbound phone calls on behalf of the user.
The agent briefs the user first, generates a call script, waits for explicit approval,
then initiates the call via ElevenLabs Conversational AI routed through Twilio.

Architecture:
- initiate_outbound_call() → POST /v1/convai/twilio/outbound-call (ElevenLabs API)
- get_call_status() → GET /v1/convai/calls/{call_id} (ElevenLabs API)
- format_call_summary() → Structure transcript into actionable summary

The ElevenLabs agent ("Paulo") has a built-in prompt and first_message with dynamic
variables ({{task_description}}, {{service_name}}, etc.). We pass call-specific data
via dynamic_variables rather than overriding the prompt, since the agent's platform
settings block prompt/first_message overrides by design.

Post-call flow: ElevenLabs webhook → webhooks.py handler → call-summary skill
"""

import asyncio
import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_API_BASE = "https://api.elevenlabs.io"


@dataclass
class CallResult:
    """Result from initiating or checking an outbound call."""

    success: bool
    call_id: str | None = None
    status: str | None = None
    error: str | None = None
    metadata: dict | None = None


@dataclass
class CallSummary:
    """Structured summary from a completed call."""

    call_id: str
    duration_seconds: int
    outcome: str  # "completed", "no_answer", "busy", "failed"
    key_points: list[str]
    action_items: list[str]
    transcript_excerpt: str
    full_transcript: str | None = None


def _get_api_key() -> str | None:
    """Get ElevenLabs API key from environment."""
    return os.environ.get("ELEVENLABS_API_KEY")


def _get_config() -> dict:
    """Get voice config from environment variables."""
    return {
        "agent_id": os.environ.get("ELEVENLABS_AGENT_ID", ""),
        "phone_number_id": os.environ.get("ELEVENLABS_PHONE_NUMBER_ID", ""),
        "pt_voice_id": os.environ.get("ELEVENLABS_PT_VOICE_ID", ""),
        "pt_caller_phone": os.environ.get("PT_CALLER_PHONE", ""),
        "twilio_account_sid": os.environ.get("TWILIO_ACCOUNT_SID", ""),
        "twilio_auth_token": os.environ.get("TWILIO_AUTH_TOKEN", ""),
    }


def is_available() -> bool:
    """Check if voice tools are configured and available."""
    api_key = _get_api_key()
    config = _get_config()
    return bool(api_key and config["agent_id"] and config["phone_number_id"])


async def initiate_outbound_call(
    to_number: str,
    task_description: str,
    service_name: str = "General",
    language: str = "pt",
    call_mode: str = "service",
    caller_name: str = "Asaf Eyzenkot",
    caller_nif: str = "299 715 477",
    caller_address: str = "Setubal, Portugal",
    entity_label: str | None = None,
    entity_notes: str | None = None,
    agent_id: str | None = None,
    phone_number_id: str | None = None,
    metadata: dict | None = None,
) -> CallResult:
    """
    Initiate an outbound phone call via ElevenLabs Conversational AI + Twilio.

    Supports two modes:
      call_mode="advisory" — Paulo calls Asaf for a conversational session (English)
      call_mode="service"  — Paulo calls a service provider on Asaf's behalf (Portuguese)

    Args:
        to_number: E.164 format phone number to call
        task_description: What the agent should achieve/discuss on this call
        service_name: Name of the entity being called
        language: Language code ("pt", "en", "es", "it")
        call_mode: "advisory" (talking to Asaf) or "service" (calling providers)
        caller_name: Person on whose behalf the call is made
        caller_nif: NIF for identity verification
        caller_address: Caller's address
        entity_label: Label for the calling entity
        entity_notes: Special context for this call
        agent_id: ElevenLabs agent ID (defaults to env var)
        phone_number_id: ElevenLabs phone number ID (defaults to env var)
        metadata: Optional dict with call context for logging

    Returns:
        CallResult with success status and call_id if successful
    """
    api_key = _get_api_key()
    if not api_key:
        return CallResult(
            success=False,
            error="ELEVENLABS_API_KEY not configured",
        )

    config = _get_config()
    resolved_agent_id = agent_id or config["agent_id"]
    resolved_phone_id = phone_number_id or config["phone_number_id"]

    if not resolved_agent_id or not resolved_phone_id:
        return CallResult(
            success=False,
            error="ElevenLabs agent_id and phone_number_id must be configured",
        )

    # Pass call-specific data via dynamic variables
    dynamic_vars = {
        "task_description": task_description,
        "service_name": service_name,
        "caller_name": caller_name,
        "caller_nif": caller_nif,
        "caller_address": caller_address,
        "entity_label": entity_label or f"{caller_name} (Personal)",
        "entity_notes": entity_notes or "Agent speaks on his behalf.",
        "call_mode": call_mode,
    }

    # Build the first_message based on call mode
    if call_mode == "advisory":
        # Calling Asaf directly — English, conversational
        first_message = f"Hello Asaf, this is Paulo. {task_description}"
        dynamic_vars["first_message_text"] = first_message
    else:
        # Calling a service provider — Portuguese, professional
        first_message = (
            f"Bom dia, o meu nome é Paulo, sou assistente pessoal "
            f"do Senhor {caller_name}, com o NIF {caller_nif}. "
            f"{task_description}"
        )
        dynamic_vars["first_message_text"] = first_message

    payload = {
        "agent_id": resolved_agent_id,
        "agent_phone_number_id": resolved_phone_id,
        "to_number": to_number,
        "conversation_initiation_client_data": {
            "conversation_config_override": {
                "agent": {
                    "first_message": first_message,
                    "language": language,
                },
            },
            # Also pass dynamic variables for the built-in prompt template
            "dynamic_variables": dynamic_vars,
        },
    }

    if metadata:
        payload["conversation_initiation_client_data"]["custom_llm_extra_body"] = {"call_metadata": metadata}

    logger.info(
        f"Initiating outbound call: {to_number} | service={service_name} | "
        f"task={task_description[:80]} | lang={language}"
    )

    last_error = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ELEVENLABS_API_BASE}/v1/convai/twilio/outbound-call",
                    headers={
                        "xi-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code in (200, 201):
                data = response.json()
                call_id = data.get("callSid") or data.get("call_id") or data.get("conversation_id")
                logger.info(f"Outbound call initiated: {call_id} → {to_number}")
                return CallResult(
                    success=True,
                    call_id=call_id,
                    status="initiated",
                    metadata=data,
                )
            elif response.status_code in (429, 500, 503) and attempt < 2:
                wait = (2**attempt) * 2.0
                logger.warning(f"ElevenLabs {response.status_code}, retrying in {wait}s (attempt {attempt + 1}/3)")
                await asyncio.sleep(wait)
                continue
            else:
                error_detail = response.text[:500]
                logger.error(f"ElevenLabs call initiation failed: {response.status_code} — {error_detail}")
                return CallResult(
                    success=False,
                    error=f"API error {response.status_code}: {error_detail}",
                )

        except httpx.TimeoutException:
            last_error = "Request timeout — ElevenLabs API did not respond within 30 seconds"
            if attempt < 2:
                logger.warning(f"ElevenLabs timeout, retrying (attempt {attempt + 1}/3)")
                await asyncio.sleep((2**attempt) * 2.0)
                continue
            return CallResult(success=False, error=last_error)
        except Exception as e:
            logger.exception(f"Unexpected error initiating call to {to_number}")
            return CallResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

    return CallResult(success=False, error=f"Failed after 3 attempts: {last_error}")


async def get_call_status(call_id: str) -> CallResult:
    """
    Poll the status of an in-progress or completed call.

    Args:
        call_id: The call ID returned by initiate_outbound_call()

    Returns:
        CallResult with current status ("initiated", "in_progress", "completed", "failed")
    """
    api_key = _get_api_key()
    if not api_key:
        return CallResult(success=False, error="ELEVENLABS_API_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{ELEVENLABS_API_BASE}/v1/convai/conversations/{call_id}",
                headers={"xi-api-key": api_key},
            )

        if response.status_code == 200:
            data = response.json()
            return CallResult(
                success=True,
                call_id=call_id,
                status=data.get("status", "unknown"),
                metadata=data,
            )
        elif response.status_code == 404:
            return CallResult(
                success=False,
                call_id=call_id,
                error="Call ID not found",
            )
        else:
            return CallResult(
                success=False,
                call_id=call_id,
                error=f"API error {response.status_code}: {response.text[:200]}",
            )

    except Exception as e:
        return CallResult(
            success=False,
            call_id=call_id,
            error=f"Error checking call status: {str(e)}",
        )


def format_call_summary(
    call_id: str,
    transcript: str | None,
    duration_seconds: int = 0,
    status: str = "completed",
) -> CallSummary:
    """
    Structure a post-call transcript into an actionable summary.

    This is called by the call-summary skill when the ElevenLabs webhook
    delivers the post-call data. It extracts key information from the
    transcript for the user.

    Args:
        call_id: The call identifier
        transcript: Full conversation transcript text
        duration_seconds: Call duration in seconds
        status: Final call status ("completed", "no_answer", "busy", "failed")

    Returns:
        CallSummary with structured output ready for user delivery
    """
    if not transcript:
        return CallSummary(
            call_id=call_id,
            duration_seconds=duration_seconds,
            outcome=status,
            key_points=["No transcript available"],
            action_items=[],
            transcript_excerpt="",
            full_transcript=None,
        )

    # Extract first 500 chars as excerpt
    transcript_excerpt = transcript[:500].strip()
    if len(transcript) > 500:
        transcript_excerpt += "..."

    # Basic extraction: lines starting with action indicators
    # In production, this feeds into the call-summary skill LLM step
    # which does the actual intelligent extraction
    lines = transcript.split("\n")
    potential_actions = [
        line.strip()
        for line in lines
        if any(
            kw in line.lower()
            for kw in [
                "will send",
                "will call back",
                "scheduled",
                "confirmed",
                "reference number",
                "case number",
                "appointment",
                "prazo",
                "será enviado",
                "ligará",
                "marcado",
                "confirmado",
            ]
        )
    ]

    return CallSummary(
        call_id=call_id,
        duration_seconds=duration_seconds,
        outcome=status,
        key_points=[f"Call {status} ({duration_seconds}s)"],
        action_items=potential_actions[:5],  # LLM step in call-summary skill refines these
        transcript_excerpt=transcript_excerpt,
        full_transcript=transcript,
    )


# Tool registry for skill executor
TOOL_FUNCTIONS = {
    "outbound_call": initiate_outbound_call,
    "call_status": get_call_status,
}
