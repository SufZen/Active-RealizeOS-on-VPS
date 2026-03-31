"""Tests for realize_core.prompt.builder — system prompt assembly.

Covers:
- Happy-path: identity, venture, agent, format, proactive layers
- Edge cases: missing files, empty venture, unknown agent, cache, truncation
- Session layer with mock session objects
- Channel format selection
- Agent-specific proactive instructions
- Layer ordering (primacy/recency optimization)
- Token budget enforcement and compression
- Cache LRU eviction and size limits
- Cross-system context capping
- Routing layer excluded for non-orchestrator agents
- Cache key normalization for Windows paths
"""

import pytest
from realize_core.prompt.builder import (
    _MAX_CACHE_SIZE,
    _build_agent_layer,
    _build_brand_layer,
    _build_cross_system_context,
    _build_identity_layer,
    _build_memory_layer,
    _build_proactive_instructions,
    _build_routing_context,
    _build_session_layer,
    _compress_layers,
    _estimate_tokens,
    _normalize_cache_key,
    _read_kb_file,
    build_system_prompt,
    clear_cache,
    get_cache_size,
    warm_cache,
)

# ---------------------------------------------------------------------------
# Fixtures (using conftest.py kb_root, system_config, shared_config)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear cache before each test to avoid cross-test pollution."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Happy-path tests (original tests, refactored to use conftest fixtures)
# ---------------------------------------------------------------------------


class TestBuildSystemPromptHappyPath:
    def test_includes_identity(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        assert "test user" in prompt.lower()

    def test_includes_venture(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        assert "Test Brand" in prompt

    def test_includes_agent(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="writer",
            shared_config=shared_config,
        )
        assert "compelling content" in prompt

    def test_includes_format_instructions_telegram(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            channel="telegram",
        )
        assert "Telegram" in prompt

    def test_includes_proactive_instructions(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        assert "proactive" in prompt.lower() or "collaboration" in prompt.lower()

    def test_includes_routing_context(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        assert "Routing" in prompt or "routing" in prompt

    def test_includes_memory_layer(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        assert "Learning" in prompt or "CTA" in prompt


# ---------------------------------------------------------------------------
# Edge cases: Missing files
# ---------------------------------------------------------------------------


class TestMissingFiles:
    def test_missing_identity_file_still_builds(self, kb_root, system_config):
        """Prompt builds even if shared identity files don't exist."""
        shared_config = {
            "identity": "nonexistent/identity.md",
            "preferences": "nonexistent/prefs.md",
        }
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        # Should still have venture, agent, proactive, format layers
        assert len(prompt) > 0
        assert "Test Brand" in prompt

    def test_missing_venture_files_still_builds(self, kb_root, shared_config):
        """Prompt builds even if venture files don't exist."""
        config = {
            "name": "NoVenture System",
            "brand_identity": "nonexistent/venture.md",
            "brand_voice": "nonexistent/voice.md",
            "agents_readme": "nonexistent/readme.md",
            "agents": {"orchestrator": "nonexistent/agent.md"},
        }
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        # Should still have identity and proactive layers
        assert len(prompt) > 0
        assert "test user" in prompt.lower()

    def test_agent_not_found_no_crash(self, kb_root, system_config, shared_config):
        """Requesting a non-existent agent doesn't crash."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="nonexistent_agent",
            shared_config=shared_config,
        )
        assert len(prompt) > 0
        # Should have identity, venture, proactive layers but no agent-specific content
        assert "Test Brand" in prompt

    def test_empty_system_config(self, kb_root, empty_system_config, shared_config):
        """Minimal system config with no files still produces a prompt."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=empty_system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        assert len(prompt) > 0


# ---------------------------------------------------------------------------
# Cache behavior
# ---------------------------------------------------------------------------


class TestCaching:
    def test_cache_hit_returns_same_content(self, kb_root):
        """Second read of the same file uses cache."""
        content1 = _read_kb_file(kb_root, "shared/identity.md")
        content2 = _read_kb_file(kb_root, "shared/identity.md")
        assert content1 == content2
        assert "test user" in content1.lower()

    def test_clear_cache_invalidates(self, kb_root):
        """After clear_cache, file is re-read from disk."""
        content1 = _read_kb_file(kb_root, "shared/identity.md")
        assert content1 != ""

        # Modify the file on disk
        (kb_root / "shared" / "identity.md").write_text("# Updated Identity\nNew content.")
        clear_cache()

        content2 = _read_kb_file(kb_root, "shared/identity.md")
        assert "New content" in content2
        assert content1 != content2

    def test_warm_cache_loads_files(self, kb_root, system_config, shared_config):
        """warm_cache pre-loads files so subsequent reads are cached."""
        systems = {"test": system_config}
        warm_cache(kb_root, systems, shared_config)

        # After warming, file should be cached
        content = _read_kb_file(kb_root, "shared/identity.md")
        assert "test user" in content.lower()


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


class TestTruncation:
    def test_file_exceeding_max_chars_is_truncated(self, kb_root):
        """Files longer than max_chars get a truncation marker."""
        # Create a large file
        large_content = "A" * 10000
        (kb_root / "shared" / "large.md").write_text(large_content)

        result = _read_kb_file(kb_root, "shared/large.md", max_chars=500)
        assert len(result) < 10000
        assert "truncated at 500 chars" in result

    def test_file_under_max_chars_not_truncated(self, kb_root):
        """Files under max_chars are returned in full."""
        content = _read_kb_file(kb_root, "shared/identity.md", max_chars=6000)
        assert "truncated" not in content


# ---------------------------------------------------------------------------
# Channel format instructions
# ---------------------------------------------------------------------------


class TestChannelFormat:
    def test_telegram_format(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            channel="telegram",
        )
        assert "Telegram" in prompt
        assert "Under 300 words" in prompt

    def test_api_format(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            channel="api",
        )
        assert "markdown" in prompt.lower()

    def test_slack_format(self, kb_root, system_config, shared_config):
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            channel="slack",
        )
        assert "Slack" in prompt

    def test_unknown_channel_defaults_to_api(self, kb_root, system_config, shared_config):
        """Unknown channels fall back to API format instructions."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            channel="whatsapp",
        )
        # Should use API format as default
        assert "Response Format" in prompt


# ---------------------------------------------------------------------------
# Session layer
# ---------------------------------------------------------------------------


class MockSession:
    """Mock session object for testing."""

    def __init__(
        self, task_type="content", stage="drafting", brief="Write a blog post", pipeline=None, pipeline_index=0
    ):
        self.task_type = task_type
        self.stage = stage
        self.brief = brief
        self.pipeline = pipeline or ["writer", "reviewer"]
        self.pipeline_index = pipeline_index


class TestSessionLayer:
    def test_session_layer_included_in_prompt(self, kb_root, system_config, shared_config):
        session = MockSession()
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="writer",
            shared_config=shared_config,
            session=session,
        )
        assert "Creative Session" in prompt
        assert "content" in prompt
        assert "drafting" in prompt

    def test_session_pipeline_progress(self):
        session = MockSession(pipeline=["writer", "reviewer", "gatekeeper"], pipeline_index=1)
        result = _build_session_layer(session)
        assert "[done] writer" in result
        assert "[ACTIVE] reviewer" in result
        assert "[next] gatekeeper" in result

    def test_session_briefing_stage(self):
        session = MockSession(stage="briefing")
        result = _build_session_layer(session)
        assert "Write a blog post" in result

    def test_no_session_returns_empty(self):
        result = _build_session_layer(None)
        assert result == ""


# ---------------------------------------------------------------------------
# Proactive instructions
# ---------------------------------------------------------------------------


class TestProactiveInstructions:
    def test_includes_collaboration_instructions(self):
        result = _build_proactive_instructions("orchestrator")
        assert "Collaboration" in result
        assert "proactive" in result.lower()

    def test_includes_pushback_protocol(self):
        result = _build_proactive_instructions("orchestrator")
        assert "Push-Back" in result

    def test_writer_specific_instructions(self):
        result = _build_proactive_instructions("writer")
        assert "content agent" in result.lower()
        assert "audience" in result.lower()

    def test_analyst_specific_instructions(self):
        result = _build_proactive_instructions("analyst")
        assert "analyst" in result.lower()
        assert "constraints" in result.lower()

    def test_generic_agent_no_specific_extras(self):
        result = _build_proactive_instructions("orchestrator")
        assert "content agent" not in result.lower()
        assert "As an analyst" not in result

    def test_session_stage_instructions(self):
        session = MockSession(stage="reviewing")
        result = _build_proactive_instructions("writer", session)
        assert "REVIEWING" in result
        assert "verdict" in result.lower()


# ---------------------------------------------------------------------------
# Individual layer builders
# ---------------------------------------------------------------------------


class TestLayerBuilders:
    def test_identity_layer_both_files(self, kb_root, shared_config):
        result = _build_identity_layer(kb_root, shared_config)
        assert "Identity" in result
        assert "Preferences" in result

    def test_venture_layer(self, kb_root, system_config):
        result = _build_brand_layer(kb_root, system_config)
        assert "Test Brand" in result
        assert "Professional" in result

    def test_agent_layer_valid(self, kb_root, system_config):
        result = _build_agent_layer(kb_root, system_config, "orchestrator")
        assert "coordinate" in result.lower()

    def test_agent_layer_invalid(self, kb_root, system_config):
        result = _build_agent_layer(kb_root, system_config, "nonexistent")
        assert result == ""

    def test_routing_context(self, kb_root, system_config):
        result = _build_routing_context(kb_root, system_config)
        assert "Routing" in result

    def test_memory_layer(self, kb_root, system_config):
        result = _build_memory_layer(kb_root, system_config)
        assert "Learning" in result or "CTA" in result

    def test_memory_layer_no_dir(self, kb_root, empty_system_config):
        result = _build_memory_layer(kb_root, empty_system_config)
        assert result == ""


# ---------------------------------------------------------------------------
# Extra context files
# ---------------------------------------------------------------------------


class TestExtraContext:
    def test_extra_context_files_loaded(self, kb_root, system_config, shared_config):
        # Create an extra file
        (kb_root / "shared" / "extra.md").write_text("# Extra\nAdditional context for the task.")

        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            extra_context_files=["shared/extra.md"],
        )
        assert "Additional context" in prompt

    def test_missing_extra_context_ignored(self, kb_root, system_config, shared_config):
        """Missing extra context files don't crash the builder."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            extra_context_files=["nonexistent/file.md"],
        )
        assert len(prompt) > 0


# ---------------------------------------------------------------------------
# Layer ordering (primacy/recency optimization)
# ---------------------------------------------------------------------------


class TestLayerOrdering:
    def test_agent_before_venture(self, kb_root, system_config, shared_config):
        """Agent definition should appear before venture identity for primacy."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="writer",
            shared_config=shared_config,
        )
        agent_pos = prompt.find("Active Agent: writer")
        venture_pos = prompt.find("Venture Identity")
        assert agent_pos > 0
        assert venture_pos > 0
        assert agent_pos < venture_pos

    def test_identity_first(self, kb_root, system_config, shared_config):
        """Identity layer should be the first layer in the prompt."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        identity_pos = prompt.find("## Identity")
        assert identity_pos >= 0
        # Identity should appear before agent and venture
        agent_pos = prompt.find("Active Agent")
        assert identity_pos < agent_pos

    def test_channel_format_last(self, kb_root, system_config, shared_config):
        """Channel format instructions should be at the end of the prompt."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            channel="telegram",
        )
        # The last separator-delimited section should contain channel format
        sections = prompt.split("\n\n---\n\n")
        last_section = sections[-1]
        assert "Telegram" in last_section or "Writing Style" in last_section


# ---------------------------------------------------------------------------
# Routing layer: orchestrator only
# ---------------------------------------------------------------------------


class TestRoutingFilter:
    def test_routing_included_for_orchestrator(self, kb_root, system_config, shared_config):
        """Routing context IS included when agent is orchestrator."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
        )
        assert "Routing" in prompt

    def test_routing_excluded_for_writer(self, kb_root, system_config, shared_config):
        """Routing context is NOT included for non-orchestrator agents."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="writer",
            shared_config=shared_config,
        )
        assert "Team Routing Guide" not in prompt


# ---------------------------------------------------------------------------
# Token budget enforcement
# ---------------------------------------------------------------------------


class TestTokenBudget:
    def test_estimate_tokens(self):
        """Token estimation: ~4 chars per token."""
        assert _estimate_tokens(400) == 100
        assert _estimate_tokens(0) == 0
        assert _estimate_tokens(3) == 0
        assert _estimate_tokens(4) == 1

    def test_compress_layers_under_budget(self):
        """Layers under budget are returned unchanged."""
        layers = [
            ("a", "short content", "identity"),
            ("b", "more content", "channel"),
        ]
        result = _compress_layers(layers, max_total_chars=10000)
        assert len(result) == 2
        assert result[0][1] == "short content"

    def test_compress_layers_over_budget(self):
        """When over budget, compressible LOW-priority layers are truncated first."""
        layers = [
            ("identity", "X" * 2000, "identity"),       # HIGH, not compressible
            ("memory", "Y" * 1500, "memory"),            # LOW, compressible → 750
            ("proactive", "Z" * 800, "proactive"),       # LOW, compressible → 400
            ("channel", "W" * 200, "channel"),            # HIGH, not compressible
        ]
        # Total: 4500. Budget: 3500. Excess: 1000.
        # memory saves 750, proactive saves 400 = 1150 savings
        result = _compress_layers(layers, max_total_chars=3500)
        # Identity and channel should be unchanged
        assert result[0][1] == "X" * 2000
        assert result[3][1] == "W" * 200
        # Memory and proactive should be compressed
        assert len(result[1][1]) < 1500
        assert "compressed" in result[1][1] or "compressed" in result[2][1]

    def test_build_prompt_respects_max_total_chars(self, kb_root, system_config, shared_config):
        """build_system_prompt accepts max_total_chars parameter."""
        prompt = build_system_prompt(
            kb_path=kb_root,
            system_config=system_config,
            system_key="test",
            agent_key="orchestrator",
            shared_config=shared_config,
            max_total_chars=50000,
        )
        # With a generous budget, all layers should be present
        assert len(prompt) > 0
        assert "Identity" in prompt


# ---------------------------------------------------------------------------
# Cache LRU eviction
# ---------------------------------------------------------------------------


class TestCacheLRU:
    def test_cache_size_limit(self, kb_root):
        """Cache should not grow beyond _MAX_CACHE_SIZE entries."""
        # Create many files
        shared = kb_root / "shared"
        for i in range(_MAX_CACHE_SIZE + 10):
            (shared / f"test_{i}.md").write_text(f"Content {i}")

        # Read them all
        for i in range(_MAX_CACHE_SIZE + 10):
            _read_kb_file(kb_root, f"shared/test_{i}.md")

        assert get_cache_size() <= _MAX_CACHE_SIZE

    def test_cache_key_normalization(self):
        """Windows backslash paths are normalized to forward slashes."""
        assert _normalize_cache_key("systems\\test\\file.md") == "systems/test/file.md"
        assert _normalize_cache_key("shared/identity.md") == "shared/identity.md"

    def test_normalized_keys_hit_same_cache(self, kb_root):
        """Forward and backslash paths should hit the same cache entry."""
        content1 = _read_kb_file(kb_root, "shared/identity.md")
        content2 = _read_kb_file(kb_root, "shared\\identity.md")
        assert content1 == content2
        assert content1 != ""


# ---------------------------------------------------------------------------
# Cross-system context capping
# ---------------------------------------------------------------------------


class TestCrossSystemCap:
    def test_cross_system_capped(self, kb_root):
        """Cross-system context should respect max_total_chars cap."""
        # Create multiple systems with large state maps
        for i in range(5):
            sys_dir = kb_root / "systems" / f"sys{i}" / "F-foundations"
            sys_dir.mkdir(parents=True)
            (sys_dir / "venture-identity.md").write_text(f"# System {i}\n{'Description ' * 200}")
            state_dir = kb_root / "systems" / f"sys{i}" / "R-routines"
            state_dir.mkdir(parents=True)
            (state_dir / "state-map.md").write_text(f"# State {i}\n{'Status info ' * 200}")

        all_systems = {
            f"sys{i}": {
                "name": f"System {i}",
                "state_map": f"systems/sys{i}/R-routines/state-map.md",
                "brand_identity": f"systems/sys{i}/F-foundations/venture-identity.md",
            }
            for i in range(5)
        }

        result = _build_cross_system_context(kb_root, "sys0", all_systems, max_total_chars=2500)
        # Result should be capped at approximately 2500 chars
        assert len(result) <= 2600  # Small buffer for truncation marker

    def test_cross_system_empty_for_single_system(self, kb_root):
        """No cross-system context when there's only one system."""
        result = _build_cross_system_context(kb_root, "only", {"only": {"name": "Only"}})
        assert result == ""

    def test_cross_system_excludes_active(self, kb_root):
        """Active system is excluded from cross-system context."""
        sys_dir = kb_root / "systems" / "active" / "F-foundations"
        sys_dir.mkdir(parents=True)
        (sys_dir / "venture-identity.md").write_text("# Active System\nI am the active one.")

        sys_dir2 = kb_root / "systems" / "other" / "F-foundations"
        sys_dir2.mkdir(parents=True)
        (sys_dir2 / "venture-identity.md").write_text("# Other System\nI am another one.")

        all_systems = {
            "active": {"name": "Active", "brand_identity": "systems/active/F-foundations/venture-identity.md"},
            "other": {"name": "Other", "brand_identity": "systems/other/F-foundations/venture-identity.md"},
        }

        result = _build_cross_system_context(kb_root, "active", all_systems)
        assert "Other" in result
        assert "Active" not in result or "Active" in result.split("Active")[0]  # Only in "active" system exclusion
