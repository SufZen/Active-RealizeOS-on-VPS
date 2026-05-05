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
        return "Read, search, and write Knowledge Base files for persistent learning and on-demand navigation"

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
            ToolSchema(
                name="kb_get",
                description=(
                    "Read the full content of a single KB file by its path. "
                    "Use kb_outline or kb_search first to discover the right path, "
                    "then call kb_get to load the content you actually need."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative path within the KB (e.g. 'systems/realization/B-brain/domain-knowledge.md')",
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": "Maximum characters to return (default 6000, ~1500 tokens)",
                            "default": 6000,
                        },
                    },
                    "required": ["file_path"],
                },
                category=self.category,
                is_destructive=False,
            ),
            ToolSchema(
                name="kb_search",
                description=(
                    "Search the KB index for files relevant to a query. "
                    "Returns file paths and one-line summaries — use kb_get to read full content. "
                    "Optionally filter by system_key or FABRIC layer."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query",
                        },
                        "system_key": {
                            "type": "string",
                            "description": "Filter to a specific venture system (e.g. 'realization', 'arena'). Optional.",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default 8)",
                            "default": 8,
                        },
                        "layer": {
                            "type": "string",
                            "description": "Filter by FABRIC layer: F (foundations), A (agents), B (brain/knowledge), R (routines), I (insights), C (creations), skill. Optional.",
                            "enum": ["F", "A", "B", "R", "I", "C", "shared", "skill"],
                        },
                    },
                    "required": ["query"],
                },
                category=self.category,
                is_destructive=False,
            ),
            ToolSchema(
                name="kb_outline",
                description=(
                    "Return a manifest table of contents for a venture system or the whole KB. "
                    "Use this to discover what files exist before deciding what to read. "
                    "Cheaper than search — returns all resources for a system/layer."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "system_key": {
                            "type": "string",
                            "description": "Filter to a specific venture system (e.g. 'realization'). Omit for all systems.",
                        },
                        "layer": {
                            "type": "string",
                            "description": "Filter by FABRIC layer: F, A, B, R, I, C, shared, skill. Optional.",
                            "enum": ["F", "A", "B", "R", "I", "C", "shared", "skill"],
                        },
                        "kind": {
                            "type": "string",
                            "description": "Filter by kind: md, agent, skill_yaml. Optional.",
                            "enum": ["md", "agent", "skill_yaml"],
                        },
                    },
                    "required": [],
                },
                category=self.category,
                is_destructive=False,
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
