"""Tests for realize_core.evolution.skill_suggester -- skill YAML validation and formatting."""

from realize_core.evolution.skill_suggester import (
    _validate_skill_yaml,
    format_skill_preview,
)


class TestValidateSkillYaml:
    def test_valid_skill(self):
        parsed = {
            "name": "weather_lookup",
            "version": "2.0",
            "description": "Look up weather",
            "steps": [
                {"id": "step1", "type": "tool", "action": "web_search"},
            ],
        }
        assert _validate_skill_yaml(parsed)

    def test_missing_name(self):
        parsed = {
            "version": "2.0",
            "steps": [{"id": "s1", "type": "tool"}],
        }
        assert not _validate_skill_yaml(parsed)

    def test_missing_version(self):
        parsed = {
            "name": "test_skill",
            "steps": [{"id": "s1", "type": "tool"}],
        }
        assert not _validate_skill_yaml(parsed)

    def test_empty_steps(self):
        parsed = {
            "name": "test_skill",
            "version": "2.0",
            "steps": [],
        }
        assert not _validate_skill_yaml(parsed)

    def test_no_steps(self):
        parsed = {
            "name": "test_skill",
            "version": "2.0",
        }
        assert not _validate_skill_yaml(parsed)

    def test_step_missing_id(self):
        parsed = {
            "name": "test_skill",
            "version": "2.0",
            "steps": [{"type": "tool"}],
        }
        assert not _validate_skill_yaml(parsed)

    def test_step_missing_type(self):
        parsed = {
            "name": "test_skill",
            "version": "2.0",
            "steps": [{"id": "s1"}],
        }
        assert not _validate_skill_yaml(parsed)

    def test_invalid_name_uppercase(self):
        parsed = {
            "name": "WeatherLookup",
            "version": "2.0",
            "steps": [{"id": "s1", "type": "tool"}],
        }
        assert not _validate_skill_yaml(parsed)

    def test_invalid_name_spaces(self):
        parsed = {
            "name": "weather lookup",
            "version": "2.0",
            "steps": [{"id": "s1", "type": "tool"}],
        }
        assert not _validate_skill_yaml(parsed)

    def test_not_a_dict(self):
        assert not _validate_skill_yaml("not a dict")
        assert not _validate_skill_yaml(None)
        assert not _validate_skill_yaml([])

    def test_multiple_steps(self):
        parsed = {
            "name": "complex_skill",
            "version": "2.0",
            "steps": [
                {"id": "s1", "type": "tool", "action": "web_search"},
                {"id": "s2", "type": "agent", "agent": "writer"},
            ],
        }
        assert _validate_skill_yaml(parsed)


class TestFormatSkillPreview:
    def test_format_valid_yaml(self):
        yaml_text = """name: test_skill
version: "2.0"
description: "A test skill"
triggers:
  - test trigger
steps:
  - id: step1
    type: tool
    label: Search
"""
        preview = format_skill_preview(yaml_text)
        assert "test_skill" in preview
        assert "A test skill" in preview

    def test_format_invalid_yaml(self):
        preview = format_skill_preview("not: [valid: yaml: {{")
        assert "```" in preview  # Falls back to code block
