"""Tests for realize_core.utils.json_utils -- shared JSON parser."""

from realize_core.utils.json_utils import parse_json_response


class TestParseJsonResponse:
    def test_plain_json(self):
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_json_fence(self):
        result = parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_markdown_fence_no_lang(self):
        result = parse_json_response('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_in_text(self):
        result = parse_json_response('Sure! Here is the result: {"action": "none"} Hope that helps.')
        assert result is not None
        assert result["action"] == "none"

    def test_nested_json(self):
        result = parse_json_response('{"outer": {"inner": "value"}}')
        assert result is not None
        assert result["outer"]["inner"] == "value"

    def test_invalid_json(self):
        result = parse_json_response("This is not JSON at all")
        assert result is None

    def test_empty_string(self):
        result = parse_json_response("")
        assert result is None

    def test_whitespace(self):
        result = parse_json_response('  {"key": "value"}  ')
        assert result == {"key": "value"}
