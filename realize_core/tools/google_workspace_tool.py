"""
BaseTool wrapper for the Google Workspace tool functions.
"""

import json
import logging

from realize_core.tools.base_tool import BaseTool, ToolCategory, ToolResult, ToolSchema

logger = logging.getLogger(__name__)


class GoogleWorkspaceTool(BaseTool):
    @property
    def name(self) -> str:
        return "google_workspace"

    @property
    def description(self) -> str:
        return "Interact with Gmail, Calendar, and Google Drive"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.PRODUCTIVITY

    def get_schemas(self) -> list[ToolSchema]:
        from realize_core.tools.google_workspace import GOOGLE_TOOL_SCHEMAS, WRITE_TOOLS

        schemas = []
        for schema in GOOGLE_TOOL_SCHEMAS:
            schemas.append(
                ToolSchema(
                    name=schema["name"],
                    description=schema["description"],
                    input_schema=schema["input_schema"],
                    category=self.category,
                    requires_auth=True,
                    is_destructive=schema["name"] in WRITE_TOOLS,
                )
            )
        return schemas

    async def execute(self, action: str, params: dict) -> ToolResult:
        from realize_core.tools.google_workspace import TOOL_FUNCTIONS

        func = TOOL_FUNCTIONS.get(action)
        if not func:
            return ToolResult.fail(f"Unknown action: {action}")

        try:
            result = await func(**params)
        except Exception as exc:
            logger.error("Google Workspace tool failed: %s", exc, exc_info=True)
            return ToolResult.fail(str(exc)[:300])

        output = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        return ToolResult.ok(output=output, data=result)

    def is_available(self) -> bool:
        try:
            import googleapiclient.discovery  # noqa: F401

            from realize_core.tools.google_auth import get_credentials

            return get_credentials() is not None
        except Exception:
            return False


def get_tool() -> GoogleWorkspaceTool:
    return GoogleWorkspaceTool()
