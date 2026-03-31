"""
BaseTool wrapper for Knowledge Base tools.
"""

import json
import logging
from typing import Any

from realize_core.tools.base_tool import BaseTool, ToolCategory, ToolResult, ToolSchema

logger = logging.getLogger(__name__)


class KBTool(BaseTool):
    @property
    def name(self) -> str:
        return "kb"

    @property
    def description(self) -> str:
        return "Append content to Knowledge Base files for persistent learning"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA

    def get_schemas(self) -> list[ToolSchema]:
        return [
            ToolSchema(
                name="kb_append",
                description=(
                    "Append content to a Knowledge Base file within the systems/ directory. "
                    "Use this to persist learnings, notes, or structured data for future reference."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative path within KB, must start with 'systems/' (e.g., 'systems/notes/learning.md')",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to append to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
                category=self.category,
                is_destructive=True,
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        from realize_core.tools.kb_tools import TOOL_FUNCTIONS

        func = TOOL_FUNCTIONS.get(action)
        if not func:
            return ToolResult.fail(f"Unknown action: {action}")

        try:
            result = await func(**params)
        except Exception as exc:
            logger.error("KB tool failed: %s", exc, exc_info=True)
            return ToolResult.fail(str(exc)[:300])

        if result.get("status") == "error":
            return ToolResult.fail(result.get("error", "Unknown error"))

        output = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        return ToolResult.ok(output=output, data=result)

    def is_available(self) -> bool:
        return True


def get_tool() -> KBTool:
    return KBTool()
