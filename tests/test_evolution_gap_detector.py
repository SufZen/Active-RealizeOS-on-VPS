"""Tests for realize_core.evolution.gap_detector -- gap detection logic."""

from realize_core.evolution.gap_detector import (
    GapDetectionConfig,
    _compute_suggestion_hash,
    _detect_low_satisfaction,
    _detect_repeated_patterns,
    _detect_tool_failures,
    _detect_unhandled_requests,
)


def _make_interaction(**overrides):
    """Helper to create a test interaction dict."""
    base = {
        "id": 1,
        "timestamp": "2026-03-30 10:00:00",
        "user_id": "user1",
        "system_key": "system1",
        "agent_key": "writer",
        "skill_name": "",
        "task_type": "",
        "tools_used": "[]",
        "intent": "",
        "message_preview": "Test message",
        "response_length": 100,
        "latency_ms": 500,
        "satisfaction_signal": "",
        "error": "",
    }
    base.update(overrides)
    return base


class TestDetectUnhandledRequests:
    def test_no_unhandled(self):
        config = GapDetectionConfig()
        interactions = [_make_interaction(tools_used='["web_search"]')]
        result = _detect_unhandled_requests(interactions, config, len(interactions))
        assert len(result) == 0

    def test_errors_count_as_unhandled(self):
        config = GapDetectionConfig(unhandled_threshold=2, min_confidence=0.0)
        interactions = [
            _make_interaction(error="Tool failed", message_preview=f"request {i}")
            for i in range(3)
        ]
        result = _detect_unhandled_requests(interactions, config, len(interactions))
        assert len(result) == 1
        assert result[0]["type"] == "unhandled_requests"

    def test_no_tools_no_skill_with_action_intent(self):
        config = GapDetectionConfig(unhandled_threshold=2, min_confidence=0.0)
        interactions = [
            _make_interaction(intent="act", message_preview=f"do thing {i}")
            for i in range(3)
        ]
        result = _detect_unhandled_requests(interactions, config, len(interactions))
        assert len(result) == 1

    def test_below_threshold(self):
        config = GapDetectionConfig(unhandled_threshold=5)
        interactions = [_make_interaction(error="fail") for _ in range(3)]
        result = _detect_unhandled_requests(interactions, config, len(interactions))
        assert len(result) == 0


class TestDetectRepeatedPatterns:
    def test_repeated_task_type(self):
        config = GapDetectionConfig(repeated_pattern_threshold=2, min_confidence=0.0)
        interactions = [
            _make_interaction(task_type="research", message_preview=f"research {i}")
            for i in range(5)
        ]
        result = _detect_repeated_patterns(interactions, config, len(interactions))
        assert len(result) == 1
        assert result[0]["type"] == "repeated_pattern"
        assert "research" in result[0]["title"]

    def test_with_skill_name_not_counted(self):
        config = GapDetectionConfig(min_confidence=0.0)
        interactions = [
            _make_interaction(task_type="research", skill_name="web_research")
            for _ in range(5)
        ]
        result = _detect_repeated_patterns(interactions, config, len(interactions))
        assert len(result) == 0  # Has skill, so not ad-hoc

    def test_below_threshold(self):
        config = GapDetectionConfig(repeated_pattern_threshold=10)
        interactions = [_make_interaction(task_type="research") for _ in range(3)]
        result = _detect_repeated_patterns(interactions, config, len(interactions))
        assert len(result) == 0


class TestDetectToolFailures:
    def test_tool_failures(self):
        config = GapDetectionConfig(tool_failure_threshold=2, min_confidence=0.0)
        interactions = [
            _make_interaction(error="timeout", tools_used='["web_search"]')
            for _ in range(3)
        ]
        result = _detect_tool_failures(interactions, config, len(interactions))
        assert len(result) == 1
        assert result[0]["type"] == "tool_failure"
        assert "web_search" in result[0]["title"]

    def test_below_threshold(self):
        config = GapDetectionConfig(tool_failure_threshold=5)
        interactions = [_make_interaction(error="fail", tools_used='["api"]')]
        result = _detect_tool_failures(interactions, config, len(interactions))
        assert len(result) == 0

    def test_no_errors(self):
        config = GapDetectionConfig()
        interactions = [_make_interaction(tools_used='["web_search"]') for _ in range(5)]
        result = _detect_tool_failures(interactions, config, len(interactions))
        assert len(result) == 0


class TestDetectLowSatisfaction:
    def test_low_satisfaction(self):
        config = GapDetectionConfig(low_satisfaction_threshold=2, min_confidence=0.0)
        interactions = [
            _make_interaction(satisfaction_signal="correction", system_key="sys1")
            for _ in range(3)
        ]
        result = _detect_low_satisfaction(interactions, config, len(interactions))
        assert len(result) == 1
        assert result[0]["type"] == "low_satisfaction"

    def test_weighted_scoring(self):
        config = GapDetectionConfig(low_satisfaction_threshold=2, min_confidence=0.0)
        interactions = [
            _make_interaction(satisfaction_signal="negative", system_key="sys1"),
            _make_interaction(satisfaction_signal="correction", system_key="sys1"),
            _make_interaction(satisfaction_signal="retry", system_key="sys1"),
        ]
        result = _detect_low_satisfaction(interactions, config, len(interactions))
        assert len(result) == 1
        # Should have weighted score > raw count
        assert "weighted" in result[0]["title"].lower()

    def test_no_negative_signals(self):
        config = GapDetectionConfig()
        interactions = [
            _make_interaction(satisfaction_signal="positive") for _ in range(5)
        ]
        result = _detect_low_satisfaction(interactions, config, len(interactions))
        assert len(result) == 0


class TestConfidenceScoring:
    def test_suggestions_have_confidence(self):
        config = GapDetectionConfig(unhandled_threshold=2, min_confidence=0.0)
        interactions = [_make_interaction(error="fail") for _ in range(10)]
        result = _detect_unhandled_requests(interactions, config, len(interactions))
        assert len(result) == 1
        assert "confidence" in result[0]
        assert 0 <= result[0]["confidence"] <= 1.0


class TestComputeSuggestionHash:
    def test_same_input_same_hash(self):
        h1 = _compute_suggestion_hash("tool_failure", "Tool X failed 5 times")
        h2 = _compute_suggestion_hash("tool_failure", "Tool X failed 5 times")
        assert h1 == h2

    def test_different_input_different_hash(self):
        h1 = _compute_suggestion_hash("tool_failure", "Tool X failed")
        h2 = _compute_suggestion_hash("tool_failure", "Tool Y failed")
        assert h1 != h2
