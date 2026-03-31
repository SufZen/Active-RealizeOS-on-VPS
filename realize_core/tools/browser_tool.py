"""
BaseTool wrapper for Playwright browser automation.
"""

import json
import logging

from realize_core.config import is_env_true
from realize_core.tools.base_tool import BaseTool, ToolCategory, ToolResult, ToolSchema

logger = logging.getLogger(__name__)


class BrowserTool(BaseTool):
    @property
    def name(self) -> str:
        return "browser"

    @property
    def description(self) -> str:
        return "Navigate and interact with web pages through a browser session"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.AUTOMATION

    def get_schemas(self) -> list[ToolSchema]:
        from realize_core.tools.browser import BROWSER_TOOL_SCHEMAS, BROWSER_WRITE_TOOLS

        schemas = []
        for schema in BROWSER_TOOL_SCHEMAS:
            schemas.append(
                ToolSchema(
                    name=schema["name"],
                    description=schema["description"],
                    input_schema=schema["input_schema"],
                    category=self.category,
                    is_destructive=schema["name"] in BROWSER_WRITE_TOOLS,
                )
            )
        return schemas

    async def execute(self, action: str, params: dict) -> ToolResult:
        from realize_core.tools.browser import TOOL_FUNCTIONS

        func = TOOL_FUNCTIONS.get(action)
        if not func:
            return ToolResult.fail(f"Unknown action: {action}")

        try:
            result = await func(**params)
        except Exception as exc:
            logger.error("Browser tool failed: %s", exc, exc_info=True)
            return ToolResult.fail(str(exc)[:300])

        output = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        return ToolResult.ok(output=output, data=result)

    def is_available(self) -> bool:
        if not is_env_true("BROWSER_ENABLED", default=False):
            return False
        try:
            import playwright.async_api  # noqa: F401
        except Exception:
            return False
        return True


def get_tool() -> BrowserTool:
    return BrowserTool()
