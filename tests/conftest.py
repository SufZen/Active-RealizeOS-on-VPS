"""Shared test fixtures for RealizeOS test suite."""

import pytest


@pytest.fixture
def kb_root(tmp_path):
    """Create a minimal KB directory structure for testing.

    Returns:
        Path to the root KB directory with:
        - shared/identity.md
        - shared/user-preferences.md
        - systems/test/F-foundations/venture-identity.md
        - systems/test/F-foundations/venture-voice.md
        - systems/test/A-agents/_README.md
        - systems/test/A-agents/orchestrator.md
        - systems/test/A-agents/writer.md
        - systems/test/I-insights/learning-log.md
    """
    # Shared identity files
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "identity.md").write_text("# Identity\nI am a test user named Alex.", encoding="utf-8")
    (shared / "user-preferences.md").write_text("# Preferences\nBe concise. Use bullet points.", encoding="utf-8")

    # System directory structure
    system_dir = tmp_path / "systems" / "test"
    system_dir.mkdir(parents=True)

    # Foundations
    foundations = system_dir / "F-foundations"
    foundations.mkdir()
    (foundations / "venture-identity.md").write_text(
        "# Venture Identity\nTest Brand Inc — AI-powered solutions for everyone.", encoding="utf-8"
    )
    (foundations / "venture-voice.md").write_text("# Venture Voice\nProfessional, direct, and friendly.", encoding="utf-8")

    # Agents
    agents = system_dir / "A-agents"
    agents.mkdir()
    (agents / "_README.md").write_text(
        "# Agent Routing\n- Orchestrator: general queries, coordination\n- Writer: content creation, blog posts, copy\n", encoding="utf-8"
    )
    (agents / "orchestrator.md").write_text("# Orchestrator\nYou coordinate the team and handle general queries.", encoding="utf-8")
    (agents / "writer.md").write_text("# Writer\nYou create compelling content and persuasive copy.", encoding="utf-8")

    # Insights / memory
    insights = system_dir / "I-insights"
    insights.mkdir()
    (insights / "learning-log.md").write_text(
        "# Learning Log\n- User prefers short paragraphs\n- Always include CTA in posts", encoding="utf-8"
    )

    return tmp_path


@pytest.fixture
def system_config():
    """Standard test system configuration dict."""
    return {
        "name": "Test System",
        "brand_identity": "systems/test/F-foundations/venture-identity.md",
        "brand_voice": "systems/test/F-foundations/venture-voice.md",
        "agents_readme": "systems/test/A-agents/_README.md",
        "memory_dir": "systems/test/I-insights",
        "insights_dir": "systems/test/I-insights",
        "agents": {
            "orchestrator": "systems/test/A-agents/orchestrator.md",
            "writer": "systems/test/A-agents/writer.md",
        },
    }


@pytest.fixture
def shared_config():
    """Standard test shared configuration dict."""
    return {
        "identity": "shared/identity.md",
        "preferences": "shared/user-preferences.md",
    }


@pytest.fixture
def empty_system_config():
    """System config with no files configured."""
    return {
        "name": "Empty System",
        "agents": {},
    }


@pytest.fixture
def minimal_yaml_config():
    """Return a minimal YAML config string for testing."""
    return """
name: "Test Business"
systems:
  - key: test
    name: "Test System"
    directory: systems/test
shared:
  identity: shared/identity.md
  preferences: shared/user-preferences.md
features:
  review_pipeline: true
  auto_memory: true
"""
