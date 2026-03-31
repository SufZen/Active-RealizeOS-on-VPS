"""Tests for realize_core.evolution.handler -- evolution intent detection."""

from realize_core.evolution.handler import (
    has_evolution_intent,
    has_strong_evolution_intent,
)


class TestHasEvolutionIntent:
    def test_save_this(self):
        assert has_evolution_intent("Save this as a new SOP")

    def test_create_new_skill(self):
        assert has_evolution_intent("Create a new skill for reporting")

    def test_update_agent(self):
        assert has_evolution_intent("Update the agent definition for writer")

    def test_evolve(self):
        assert has_evolution_intent("Let's evolve the system")

    def test_remember_this(self):
        assert has_evolution_intent("Remember this as a rule for next time")

    def test_add_to_kb(self):
        assert has_evolution_intent("Add this to the knowledge base")

    def test_normal_question_no_intent(self):
        assert not has_evolution_intent("What's the weather like?")

    def test_normal_request_no_intent(self):
        assert not has_evolution_intent("Write me a blog post about AI")

    def test_greeting_no_intent(self):
        assert not has_evolution_intent("Hello, how are you?")


class TestHasStrongEvolutionIntent:
    def test_save_this_to(self):
        assert has_strong_evolution_intent("Save this to the brain")

    def test_create_new_sop(self):
        assert has_strong_evolution_intent("Create a new SOP for onboarding")

    def test_update_state_map(self):
        assert has_strong_evolution_intent("Update the state map with new metrics")

    def test_normal_message_no_strong_intent(self):
        assert not has_strong_evolution_intent("Please help me with this task")

    def test_weak_intent_not_strong(self):
        # "evolve" is a weak signal, not strong
        assert not has_strong_evolution_intent("Let's evolve")


class TestParseJsonResponse:
    def test_plain_json(self):
        from realize_core.evolution.handler import _parse_json_response

        result = _parse_json_response('{"action": "none"}')
        assert result == {"action": "none"}

    def test_markdown_fenced(self):
        from realize_core.evolution.handler import _parse_json_response

        result = _parse_json_response('```json\n{"action": "create_file"}\n```')
        assert result is not None
        assert result["action"] == "create_file"

    def test_json_in_text(self):
        from realize_core.evolution.handler import _parse_json_response

        result = _parse_json_response('Here is the result: {"action": "none"} and more text')
        assert result is not None
        assert result["action"] == "none"

    def test_invalid_json(self):
        from realize_core.evolution.handler import _parse_json_response

        result = _parse_json_response("This is not JSON at all")
        assert result is None

    def test_empty_string(self):
        from realize_core.evolution.handler import _parse_json_response

        result = _parse_json_response("")
        assert result is None
