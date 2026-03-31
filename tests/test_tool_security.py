"""Security tests for the tools system: SSRF, path traversal, truncation, timing."""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from realize_core.tools.base_tool import BaseTool, ToolCategory, ToolResult, ToolSchema
from realize_core.tools.tool_registry import ToolRegistry
from realize_core.tools.web import validate_url

# ---------------------------------------------------------------------------
# SSRF / URL Validation Tests
# ---------------------------------------------------------------------------


def _mock_resolve_public(hostname, *args, **kwargs):
    """Mock DNS resolution: return a public IP for known test domains."""
    public_domains = {"example.com", "www.google.com", "api.example.com"}
    if hostname in public_domains:
        return [(2, 1, 6, "", ("93.184.216.34", 0))]
    raise OSError(f"Cannot resolve {hostname}")


class TestURLValidation:
    """Test SSRF protection via URL validation."""

    @patch("realize_core.tools.web.socket.getaddrinfo", side_effect=_mock_resolve_public)
    def test_valid_https_url(self, mock_dns):
        assert validate_url("https://example.com") is None

    @patch("realize_core.tools.web.socket.getaddrinfo", side_effect=_mock_resolve_public)
    def test_valid_http_url(self, mock_dns):
        assert validate_url("http://example.com") is None

    def test_block_file_scheme(self):
        err = validate_url("file:///etc/passwd")
        assert err is not None
        assert "scheme" in err.lower()

    def test_block_ftp_scheme(self):
        err = validate_url("ftp://example.com/file")
        assert err is not None
        assert "scheme" in err.lower()

    def test_block_javascript_scheme(self):
        err = validate_url("javascript:alert(1)")
        assert err is not None
        assert "scheme" in err.lower()

    def test_block_data_scheme(self):
        err = validate_url("data:text/html,<h1>hi</h1>")
        assert err is not None
        assert "scheme" in err.lower()

    def test_block_localhost(self):
        err = validate_url("http://localhost/admin")
        assert err is not None
        assert "blocked" in err.lower() or "private" in err.lower()

    @patch("realize_core.tools.web.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 0))])
    def test_block_127_0_0_1(self, mock_dns):
        err = validate_url("http://127.0.0.1/")
        assert err is not None
        assert "private" in err.lower() or "blocked" in err.lower()

    @patch("realize_core.tools.web.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("169.254.169.254", 0))])
    def test_block_metadata_endpoint(self, mock_dns):
        """Block cloud metadata endpoints (169.254.169.254)."""
        err = validate_url("http://169.254.169.254/latest/meta-data/")
        assert err is not None

    @patch("realize_core.tools.web.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.1", 0))])
    def test_block_private_10_range(self, mock_dns):
        err = validate_url("http://10.0.0.1/")
        assert err is not None

    @patch("realize_core.tools.web.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("172.16.0.1", 0))])
    def test_block_private_172_range(self, mock_dns):
        err = validate_url("http://172.16.0.1/")
        assert err is not None

    @patch("realize_core.tools.web.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("192.168.1.1", 0))])
    def test_block_private_192_168_range(self, mock_dns):
        err = validate_url("http://192.168.1.1/")
        assert err is not None

    @patch("realize_core.tools.web.socket.getaddrinfo", return_value=[(10, 1, 6, "", ("::1", 0, 0, 0))])
    def test_block_ipv6_loopback(self, mock_dns):
        err = validate_url("http://[::1]/")
        assert err is not None

    def test_block_no_hostname(self):
        err = validate_url("http:///path")
        assert err is not None

    def test_block_empty_string(self):
        err = validate_url("")
        assert err is not None

    def test_block_google_metadata(self):
        err = validate_url("http://metadata.google.internal/computeMetadata/v1/")
        assert err is not None
        assert "blocked" in err.lower()

    @patch("realize_core.tools.web.socket.getaddrinfo", side_effect=_mock_resolve_public)
    def test_allow_valid_external(self, mock_dns):
        """Public URLs should pass validation."""
        assert validate_url("https://www.google.com/search?q=test") is None
        assert validate_url("https://api.example.com/v1/data") is None


# ---------------------------------------------------------------------------
# KB Path Traversal Tests
# ---------------------------------------------------------------------------


class TestKBPathTraversal:
    """Test that KB tools prevent path traversal attacks."""

    @pytest.mark.asyncio
    async def test_reject_double_dot(self):
        from realize_core.tools.kb_tools import kb_append

        result = await kb_append("systems/../../etc/passwd", "test")
        assert result["status"] == "error"
        assert "traversal" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reject_non_systems_path(self):
        from realize_core.tools.kb_tools import kb_append

        result = await kb_append("etc/passwd", "test")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_reject_path_escaping_base(self):
        """Even without '..' in parts, resolved path must stay in KB base."""
        from realize_core.tools.kb_tools import kb_append

        # This has '..' which gets caught by the first check
        result = await kb_append("systems/../../../tmp/evil", "test")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_valid_systems_path(self):
        """A valid systems/ path should work."""
        from realize_core.tools.kb_tools import kb_append

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await kb_append(
                "systems/test/note.md", "test content", kb_path=tmpdir
            )
            assert result["status"] == "ok"
            assert result["bytes_written"] > 0
            # Verify file was created
            expected = Path(tmpdir) / "systems" / "test" / "note.md"
            assert expected.exists()


# ---------------------------------------------------------------------------
# Registry Result Truncation Tests
# ---------------------------------------------------------------------------


class _LargeOutputTool(BaseTool):
    """Test tool that produces very large output."""

    @property
    def name(self) -> str:
        return "large_output"

    @property
    def description(self) -> str:
        return "Produces large output"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CUSTOM

    def get_schemas(self) -> list[ToolSchema]:
        return [
            ToolSchema(
                name="large_action",
                description="Returns a lot of text",
                input_schema={"type": "object", "properties": {}},
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        # Generate output larger than MAX_RESULT_CHARS (12000)
        return ToolResult.ok("X" * 20000)

    def is_available(self) -> bool:
        return True


class TestResultTruncation:
    @pytest.mark.asyncio
    async def test_truncation_large_output(self):
        reg = ToolRegistry()
        reg.register(_LargeOutputTool())
        result = await reg.execute("large_action", {})
        assert result.success
        assert len(result.output) <= reg.MAX_RESULT_CHARS + 50  # Allow for truncation marker
        assert "[...truncated]" in result.output
        assert result.metadata.get("truncated") is True

    @pytest.mark.asyncio
    async def test_no_truncation_small_output(self):
        from tests.test_tool_sdk import MockTool

        reg = ToolRegistry()
        reg.register(MockTool())
        result = await reg.execute("mock_read", {"key": "test"})
        assert result.success
        assert result.metadata.get("truncated") is None


# ---------------------------------------------------------------------------
# Execution Timing Tests
# ---------------------------------------------------------------------------


class TestExecutionTiming:
    @pytest.mark.asyncio
    async def test_timing_metadata(self):
        from tests.test_tool_sdk import MockTool

        reg = ToolRegistry()
        reg.register(MockTool())
        result = await reg.execute("mock_read", {"key": "test"})
        assert result.success
        assert "duration_ms" in result.metadata
        assert isinstance(result.metadata["duration_ms"], int)
        assert result.metadata["duration_ms"] >= 0


# ---------------------------------------------------------------------------
# Registry Health Check Tests
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_health_check_returns_availability(self):
        from tests.test_tool_sdk import MockTool, UnavailableTool

        reg = ToolRegistry()
        reg.register(MockTool())
        reg.register(UnavailableTool())
        health = reg.check_health()
        assert health["mock_tool"] is True
        assert health["unavailable_tool"] is False
