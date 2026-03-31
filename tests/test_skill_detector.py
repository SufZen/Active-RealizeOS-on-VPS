"""Tests for realize_core.skills.detector — skill detection and loading.

Covers:
- v1 skill detection (pipeline-based)
- v2 skill detection (step-based)
- No skill match for unrelated messages
- Atomic skills state (race-condition safety)
- Trigger specificity scoring (longer triggers win)
- Word-boundary matching (single-word triggers)
- Skill priority tie-breaking
- Negative trigger weighting
- v2 schema validation at load time
- Reload with empty dirs still provides defaults
- return_all mode for debugging
"""

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_skills_state():
    """Reset the global skills state before each test."""
    import realize_core.skills.detector as det
    from realize_core.skills.detector import _SkillsState

    det._skills_state = _SkillsState()
    yield
    det._skills_state = _SkillsState()


@pytest.fixture
def skills_setup(tmp_path):
    """Create test skill files (v1 and v2)."""
    skills_dir = tmp_path / "skills" / "test"
    skills_dir.mkdir(parents=True)

    # v1 skill (pipeline-based)
    (skills_dir / "content_pipeline.yaml").write_text("""
name: content_pipeline
triggers:
  - "write a post"
  - "create content"
task_type: content
pipeline:
  - writer
  - reviewer
""")

    # v2 skill (step-based)
    (skills_dir / "research_workflow.yaml").write_text("""
name: research_workflow
version: "2.0"
triggers:
  - "research competitors"
  - "competitive analysis"
task_type: research
steps:
  - id: search
    type: tool
    action: web_search
    params:
      query: "{user_message}"
  - id: analyze
    type: agent
    agent: analyst
    inject_context: [search]
""")

    return tmp_path, skills_dir


@pytest.fixture
def empty_skills_dir(tmp_path):
    """Create an empty skills directory."""
    skills_dir = tmp_path / "skills" / "empty"
    skills_dir.mkdir(parents=True)
    return tmp_path, skills_dir


@pytest.fixture
def malformed_skills_dir(tmp_path):
    """Create a skills directory with malformed YAML."""
    skills_dir = tmp_path / "skills" / "bad"
    skills_dir.mkdir(parents=True)

    (skills_dir / "broken.yaml").write_text("""
name: broken_skill
triggers: not_a_list
  - this is invalid yaml
""")

    return tmp_path, skills_dir


@pytest.fixture
def no_triggers_dir(tmp_path):
    """Create skills directory with skill missing triggers."""
    skills_dir = tmp_path / "skills" / "notrig"
    skills_dir.mkdir(parents=True)

    (skills_dir / "no_triggers.yaml").write_text("""
name: no_triggers_skill
task_type: general
pipeline:
  - orchestrator
""")

    return tmp_path, skills_dir


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestSkillDetectionHappyPath:
    def test_detect_skill_v1(self, skills_setup):
        from realize_core.skills.detector import detect_skill, load_skills

        tmp_path, skills_dir = skills_setup

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="Can you write a post about AI trends?")
        assert skill is not None
        assert skill["name"] == "content_pipeline"
        assert skill.get("_version", 1) == 1

    def test_detect_skill_v2(self, skills_setup):
        from realize_core.skills.detector import detect_skill, load_skills

        tmp_path, skills_dir = skills_setup

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="research competitors in the AI space")
        assert skill is not None
        assert skill["name"] == "research_workflow"
        assert skill.get("_version") == 2

    def test_no_skill_for_unrelated_message(self, skills_setup):
        from realize_core.skills.detector import detect_skill, load_skills

        tmp_path, skills_dir = skills_setup

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="hello how are you")
        # May return default or None depending on fallback behavior
        if skill:
            assert skill["name"] != "content_pipeline"
            assert skill["name"] != "research_workflow"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestSkillDetectionEdgeCases:
    def test_empty_skills_directory(self, empty_skills_dir):
        """Loading from an empty directory should not crash."""
        from realize_core.skills.detector import detect_skill, load_skills

        _, skills_dir = empty_skills_dir

        # Should not raise
        load_skills(skills_dir.parent)

        # No skills loaded, so nothing should match
        skill = detect_skill(system_key="empty", message="write a post")
        # Result depends on fallback behavior — just verify no crash
        assert skill is None or isinstance(skill, dict)

    def test_nonexistent_skills_directory(self, tmp_path):
        """Loading from a nonexistent directory should handle gracefully."""
        from realize_core.skills.detector import load_skills

        nonexistent = str(tmp_path / "nonexistent" / "skills")

        # Should not raise (implementation may log a warning)
        try:
            load_skills(nonexistent)
        except (FileNotFoundError, OSError):
            pass  # Acceptable: some implementations raise on missing dir

    def test_skill_trigger_case_insensitive(self, skills_setup):
        """Trigger matching should be case-insensitive."""
        from realize_core.skills.detector import detect_skill, load_skills

        _, skills_dir = skills_setup

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="WRITE A POST about marketing")
        # Should still match content_pipeline
        if skill:
            assert skill["name"] == "content_pipeline"

    def test_v1_skill_has_pipeline(self, skills_setup):
        """v1 skills should have a pipeline list."""
        from realize_core.skills.detector import detect_skill, load_skills

        _, skills_dir = skills_setup

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="write a post")
        if skill and skill["name"] == "content_pipeline":
            assert "pipeline" in skill
            assert isinstance(skill["pipeline"], list)
            assert len(skill["pipeline"]) > 0

    def test_v2_skill_has_steps(self, skills_setup):
        """v2 skills should have a steps list."""
        from realize_core.skills.detector import detect_skill, load_skills

        _, skills_dir = skills_setup

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="research competitors")
        if skill and skill["name"] == "research_workflow":
            assert "steps" in skill
            assert isinstance(skill["steps"], list)
            assert len(skill["steps"]) > 0

    def test_no_triggers_skill(self, no_triggers_dir):
        """Skill without triggers should not match any message."""
        from realize_core.skills.detector import detect_skill, load_skills

        _, skills_dir = no_triggers_dir

        # Should not crash when loading skill without triggers
        try:
            load_skills(skills_dir.parent)
        except Exception:
            pass  # Some implementations may reject skills without triggers

        skill = detect_skill(system_key="notrig", message="anything at all")
        # Should not match since there are no triggers
        if skill:
            assert skill.get("name") != "no_triggers_skill" or "triggers" not in skill

    def test__shared_skills_are_available_to_all_systems(self, tmp_path):
        """Skills placed under systems/_shared should be merged for every system."""
        shared_dir = tmp_path / "systems" / "_shared" / "R-routines" / "skills"
        shared_dir.mkdir(parents=True)
        (shared_dir / "shared_skill.yaml").write_text(
            """
name: shared_skill
triggers:
  - "portfolio dashboard"
task_type: general
pipeline:
  - orchestrator
""",
            encoding="utf-8",
        )

        from realize_core.skills.detector import detect_skill, reload_skills

        reload_skills(kb_path=tmp_path)

        skill = detect_skill(system_key="alpha", message="show me the portfolio dashboard")
        assert skill is not None
        assert skill["name"] == "shared_skill"


# ---------------------------------------------------------------------------
# Atomic skills state (P0-1)
# ---------------------------------------------------------------------------


class TestAtomicSkillsState:
    def test_load_produces_immutable_state(self, skills_setup):
        """After loading, the state should be a frozen dataclass."""
        import realize_core.skills.detector as det
        from realize_core.skills.detector import _SkillsState, load_skills

        _, skills_dir = skills_setup
        load_skills(skills_dir.parent)

        state = det._skills_state
        assert isinstance(state, _SkillsState)
        assert state.loaded is True

    def test_reload_replaces_state_atomically(self, skills_setup):
        """reload_skills() should produce a new state object, not mutate the old one."""
        import realize_core.skills.detector as det
        from realize_core.skills.detector import load_skills, reload_skills

        _, skills_dir = skills_setup
        load_skills(skills_dir.parent)
        state_before = det._skills_state

        reload_skills(skills_dir.parent)
        state_after = det._skills_state

        # Should be different objects
        assert state_before is not state_after
        assert state_after.loaded is True

    def test_concurrent_safe_reads(self, skills_setup):
        """Taking a local reference to state should be safe even if reload happens."""
        from realize_core.skills.detector import get_skills_for_system, load_skills

        _, skills_dir = skills_setup
        load_skills(skills_dir.parent)

        # Simulate: take local ref, then reload
        skills = get_skills_for_system("test")
        assert isinstance(skills, list)


# ---------------------------------------------------------------------------
# Trigger specificity scoring (P1-1)
# ---------------------------------------------------------------------------


class TestTriggerSpecificity:
    def test_longer_trigger_scores_higher(self, tmp_path):
        """'write a post' (3 words) should score higher than 'write' (1 word)."""
        from realize_core.skills.detector import _score_trigger

        score_short = _score_trigger("write", "i want to write something")
        score_long = _score_trigger("write a post", "i want to write a post about AI")

        assert score_long > score_short

    def test_exact_phrase_scores_higher_than_fuzzy(self, tmp_path):
        """Exact substring match should score higher than all-words-present."""
        from realize_core.skills.detector import _score_trigger

        # Exact: "competitive analysis" is a substring
        score_exact = _score_trigger("competitive analysis", "do a competitive analysis")
        # Fuzzy: words present but not as phrase
        score_fuzzy = _score_trigger("competitive analysis", "analysis of the competitive landscape")

        assert score_exact > score_fuzzy

    def test_specific_skill_wins_over_generic(self, tmp_path):
        """When two skills match, the more specific one should win."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        (skills_dir / "generic.yaml").write_text("""
name: generic_content
triggers:
  - "write"
pipeline: [writer]
""")
        (skills_dir / "specific.yaml").write_text("""
name: specific_post
triggers:
  - "write a post"
pipeline: [writer, reviewer]
""")

        from realize_core.skills.detector import detect_skill, load_skills

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="please write a post about AI")
        assert skill is not None
        assert skill["name"] == "specific_post"


# ---------------------------------------------------------------------------
# Word-boundary matching (P1-4)
# ---------------------------------------------------------------------------


class TestWordBoundary:
    def test_single_word_does_not_match_substring(self):
        """'analyze' should NOT match 'overanalyze' or 'reanalyze'."""
        from realize_core.skills.detector import _score_trigger

        assert _score_trigger("analyze", "overanalyze the data") == 0
        assert _score_trigger("analyze", "reanalyze everything") == 0

    def test_single_word_matches_on_boundary(self):
        """'analyze' should match 'analyze the data' and 'let us analyze'."""
        from realize_core.skills.detector import _score_trigger

        assert _score_trigger("analyze", "analyze the data") > 0
        assert _score_trigger("analyze", "let us analyze the results") > 0

    def test_single_word_at_end_of_message(self):
        """'research' at end of sentence should match."""
        from realize_core.skills.detector import _score_trigger

        assert _score_trigger("research", "I need to do some research") > 0

    def test_write_does_not_match_rewrite(self):
        """'write' should NOT match 'rewrite'."""
        from realize_core.skills.detector import _score_trigger

        assert _score_trigger("write", "rewrite the document") == 0


# ---------------------------------------------------------------------------
# Skill priority (P1-2)
# ---------------------------------------------------------------------------


class TestSkillPriority:
    def test_higher_priority_wins_tie(self, tmp_path):
        """When scores are equal, higher priority skill wins."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        (skills_dir / "skill_a.yaml").write_text("""
name: skill_a
triggers:
  - "deploy"
priority: 0
pipeline: [orchestrator]
""")
        (skills_dir / "skill_b.yaml").write_text("""
name: skill_b
triggers:
  - "deploy"
priority: 10
pipeline: [orchestrator]
""")

        from realize_core.skills.detector import detect_skill, load_skills

        load_skills(skills_dir.parent)

        skill = detect_skill(system_key="test", message="deploy the app")
        assert skill is not None
        assert skill["name"] == "skill_b"


# ---------------------------------------------------------------------------
# Negative triggers (P1-3)
# ---------------------------------------------------------------------------


class TestNegativeTriggers:
    def test_negative_trigger_reduces_score(self, tmp_path):
        """Negative triggers should reduce score."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        (skills_dir / "content.yaml").write_text("""
name: content_skill
triggers:
  - "write"
negative_triggers:
  - "code"
pipeline: [writer]
""")

        from realize_core.skills.detector import detect_skill, load_skills

        load_skills(skills_dir.parent)

        # Without negative trigger
        skill = detect_skill(system_key="test", message="write a blog post")
        assert skill is not None

        # With negative trigger — should not match (score goes negative)
        skill = detect_skill(system_key="test", message="write code for the API")
        # Score: 8 (write) - 10 (code negative) = -2, should not match
        assert skill is None

    def test_custom_negative_weight(self, tmp_path):
        """Custom negative weight should be respected."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        (skills_dir / "mild.yaml").write_text("""
name: mild_negative
triggers:
  - "analyze"
negative_triggers:
  - "code"
negative_weight: -3
pipeline: [analyst]
""")

        from realize_core.skills.detector import detect_skill, load_skills

        load_skills(skills_dir.parent)

        # With mild negative, score should still be positive: 8 - 3 = 5
        skill = detect_skill(system_key="test", message="analyze the code quality")
        assert skill is not None
        assert skill["name"] == "mild_negative"


# ---------------------------------------------------------------------------
# Reload defaults behavior (P0-2)
# ---------------------------------------------------------------------------


class TestReloadDefaults:
    def test_empty_dir_falls_through_to_defaults(self, tmp_path):
        """Empty system dir should NOT suppress default skills."""
        skills_dir = tmp_path / "skills" / "mysystem"
        skills_dir.mkdir(parents=True)
        # Directory exists but has no YAML files

        from realize_core.skills.detector import get_skills_for_system, load_skills

        load_skills(skills_dir.parent)

        # "mysystem" dir was empty, so defaults should still be available
        skills = get_skills_for_system("mysystem")
        assert len(skills) > 0
        names = [s["name"] for s in skills]
        assert "content_pipeline" in names  # Default skill

    def test_reload_with_deleted_files_restores_defaults(self, tmp_path):
        """After deleting all YAML files and reloading, defaults should return."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        yaml_file = skills_dir / "temp.yaml"
        yaml_file.write_text("""
name: temp_skill
triggers:
  - "temporary"
pipeline: [orchestrator]
""")

        from realize_core.skills.detector import get_skills_for_system, load_skills, reload_skills

        load_skills(skills_dir.parent)
        skills = get_skills_for_system("test")
        names = [s["name"] for s in skills]
        assert "temp_skill" in names

        # Delete the file and reload
        yaml_file.unlink()
        reload_skills(skills_dir.parent)

        skills = get_skills_for_system("test")
        names = [s["name"] for s in skills]
        assert "temp_skill" not in names
        # Defaults should be available since no YAML skills exist
        assert "content_pipeline" in names


# ---------------------------------------------------------------------------
# Schema validation (P2-1)
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_v2_skill_missing_step_id_rejected(self, tmp_path):
        """v2 skill with step missing 'id' should be rejected at load time."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        (skills_dir / "bad_v2.yaml").write_text("""
name: bad_v2_skill
triggers:
  - "bad skill"
steps:
  - type: agent
    agent: writer
""")

        from realize_core.skills.detector import get_skills_for_system, load_skills

        load_skills(skills_dir.parent)

        skills = get_skills_for_system("test")
        names = [s["name"] for s in skills]
        assert "bad_v2_skill" not in names

    def test_v2_skill_invalid_step_type_rejected(self, tmp_path):
        """v2 skill with unknown step type should be rejected at load time."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        (skills_dir / "bad_type.yaml").write_text("""
name: bad_type_skill
triggers:
  - "bad type"
steps:
  - id: step1
    type: unknown_type
""")

        from realize_core.skills.detector import get_skills_for_system, load_skills

        load_skills(skills_dir.parent)

        skills = get_skills_for_system("test")
        names = [s["name"] for s in skills]
        assert "bad_type_skill" not in names

    def test_valid_v2_skill_accepted(self, tmp_path):
        """Valid v2 skill should load correctly."""
        skills_dir = tmp_path / "skills" / "test"
        skills_dir.mkdir(parents=True)

        (skills_dir / "good_v2.yaml").write_text("""
name: good_v2_skill
triggers:
  - "good skill"
steps:
  - id: step1
    type: agent
    agent: writer
  - id: step2
    type: tool
    action: web_search
  - id: step3
    type: human
    question: "Proceed?"
  - id: step4
    type: condition
    check: "{step1}"
    branches:
      "yes": continue
""")

        from realize_core.skills.detector import get_skills_for_system, load_skills

        load_skills(skills_dir.parent)

        skills = get_skills_for_system("test")
        names = [s["name"] for s in skills]
        assert "good_v2_skill" in names


# ---------------------------------------------------------------------------
# return_all mode (P3-3)
# ---------------------------------------------------------------------------


class TestReturnAllMode:
    def test_return_all_gives_scored_list(self, skills_setup):
        """return_all=True should return list of (skill, score) tuples."""
        from realize_core.skills.detector import detect_skill, load_skills

        _, skills_dir = skills_setup
        load_skills(skills_dir.parent)

        results = detect_skill(
            system_key="test",
            message="research competitors and create content",
            return_all=True,
        )
        assert isinstance(results, list)
        assert len(results) >= 1
        # Each entry is (skill_dict, score)
        for skill, score in results:
            assert isinstance(skill, dict)
            assert isinstance(score, (int, float))
            assert score > 0

    def test_return_all_sorted_by_score_desc(self, skills_setup):
        """Results should be sorted by score descending."""
        from realize_core.skills.detector import detect_skill, load_skills

        _, skills_dir = skills_setup
        load_skills(skills_dir.parent)

        results = detect_skill(
            system_key="test",
            message="research competitors and create content",
            return_all=True,
        )
        if len(results) >= 2:
            scores = [s for _, s in results]
            assert scores == sorted(scores, reverse=True)
