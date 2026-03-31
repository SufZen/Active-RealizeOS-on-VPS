"""
BaseTool wrapper for Voice/Phone tools (ElevenLabs + Twilio).
"""

import json
import logging
from typing import Any

from realize_core.tools.base_tool import BaseTool, ToolCategory, ToolResult, ToolSchema

logger = logging.getLogger(__name__)


class VoiceTool(BaseTool):
    @property
    def name(self) -> str:
        return "voice"

    @property
    def description(self) -> str:
        return "Initiate and monitor outbound phone calls via ElevenLabs AI + Twilio"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATION

    def get_schemas(self) -> list[ToolSchema]:
        return [
            ToolSchema(
                name="outbound_call",
                description=(
                    "Initiate an outbound phone call via ElevenLabs Conversational AI + Twilio. "
                    "The AI agent (Paulo) calls the specified number and handles the conversation. "
                    "Use call_mode='service' for calling service providers (Portuguese) or "
                    "'advisory' for calling Asaf directly (English). Requires explicit user approval."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "to_number": {
                            "type": "string",
                            "description": "Phone number in E.164 format (e.g., '+351912345678')",
                        },
                        "task_description": {
                            "type": "string",
                            "description": "What the agent should achieve on this call",
                        },
                        "service_name": {
                            "type": "string",
                            "description": "Name of the entity being called (default: 'General')",
                        },
                        "language": {
                            "type": "string",
                            "enum": ["pt", "en", "es", "it"],
                            "description": "Language for the call (default: 'pt')",
                        },
                        "call_mode": {
                            "type": "string",
                            "enum": ["service", "advisory"],
                            "description": "'service' = calling providers on behalf of user, 'advisory' = calling Asaf directly",
                        },
                    },
                    "required": ["to_number", "task_description"],
                },
                category=self.category,
                requires_auth=True,
                is_destructive=True,
            ),
            ToolSchema(
                name="call_status",
                description=(
                    "Check the status of an in-progress or completed phone call. "
                    "Returns: 'initiated', 'in_progress', 'completed', or 'failed'."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "call_id": {
                            "type": "string",
                            "description": "Call ID returned by outbound_call",
                        },
                    },
                    "required": ["call_id"],
                },
                category=self.category,
                requires_auth=True,
                is_destructive=False,
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        from realize_core.tools.voice_tools import TOOL_FUNCTIONS

        func = TOOL_FUNCTIONS.get(action)
        if not func:
            return ToolResult.fail(f"Unknown action: {action}")

        try:
            result = await func(**params)
        except Exception as exc:
            logger.error("Voice tool failed: %s", exc, exc_info=True)
            return ToolResult.fail(str(exc)[:300])

        # CallResult dataclass → dict
        if hasattr(result, "__dataclass_fields__"):
            result_dict = {
                "success": result.success,
                "call_id": result.call_id,
                "status": result.status,
                "error": result.error,
            }
            if not result.success:
                return ToolResult.fail(result.error or "Call failed")
            output = json.dumps(result_dict, indent=2, default=str, ensure_ascii=False)
            return ToolResult.ok(output=output, data=result_dict)

        output = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        return ToolResult.ok(output=output, data=result)

    def is_available(self) -> bool:
        try:
            from realize_core.tools.voice_tools import is_available

            return is_available()
        except Exception:
            return False


def get_tool() -> VoiceTool:
    return VoiceTool()
