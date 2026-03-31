"""Tests for realize_core.skills.executor — multi-step skill execution engine.

Covers:
- SkillContext: variable injection, step result tracking
- Resume context storage and retrieval (keyed by system_key + user_id)
- v1 pipeline skill execution (mocked LLM)
- v2 step-based skill execution (mocked LLM, tools)
- Condition step branching (enhanced operators)
- Human-in-the-loop pausing
- Step error isolation
- Agent step uses route_to_llm (not call_claude)
- Lazy tool registry
- Dry-run mode
- Execution audit log
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from realize_core.skills.executor import (
    SkillContext,
    SkillExecutionLog,
    _match_condition,
    _pending_skill_contexts,
    _process_step_result,
    execute_skill,
    pop_skill_resume_context,
    store_skill_resume_context,
)

# ---------------------------------------------------------------------------
# SkillContext
# ---------------------------------------------------------------------------


class TestSkillContext:
    def test_init(self):
        ctx = SkillContext("write a blog post", "venture1", "user1")
        assert ctx.user_message == "write a blog post"
        assert ctx.system_key == "venture1"
        assert ctx.user_id == "user1"
        assert ctx.step_results == {}
        assert ctx.variables["doc_title"] == "write a blog post"

    def test_inject_user_message(self):
        ctx = SkillContext("AI trends 2026", "venture1", "user1")
        result = ctx.inject("Write about: {user_message}")
        assert result == "Write about: AI trends 2026"

    def test_inject_step_result(self):
        ctx = SkillContext("test", "s1", "u1")
        ctx.step_results["search"] = "Found 3 competitors"
        result = ctx.inject("Based on research: {search}")
        assert result == "Based on research: Found 3 competitors"

    def test_inject_variable(self):
        ctx = SkillContext("test doc", "s1", "u1")
        ctx.variables["output_format"] = "markdown"
        result = ctx.inject("Format: {output_format}")
        assert result == "Format: markdown"

    def test_inject_today_date(self):
        ctx = SkillContext("test", "s1", "u1")
        result = ctx.inject("Report for {today}")
        expected = date.today().isoformat()
        assert expected in result

    def test_inject_multiple_placeholders(self):
        ctx = SkillContext("AI article", "s1", "u1")
        ctx.step_results["draft"] = "First draft content"
        ctx.variables["tone"] = "professional"
        result = ctx.inject("Topic: {user_message}, Tone: {tone}, Draft: {draft}")
        assert "AI article" in result
        assert "professional" in result
        assert "First draft content" in result

    def test_inject_missing_placeholder_unchanged(self):
        ctx = SkillContext("test", "s1", "u1")
        result = ctx.inject("Value: {nonexistent}")
        # Unresolved placeholders remain as-is
        assert "{nonexistent}" in result

    def test_progress_tracking(self):
        ctx = SkillContext("test", "s1", "u1")
        ctx.progress_messages.append("Step 1: done")
        ctx.progress_messages.append("Step 2: done")
        assert len(ctx.progress_messages) == 2


# ---------------------------------------------------------------------------
# Resume context storage (P0-3: keyed by system_key + user_id)
# ---------------------------------------------------------------------------


class TestResumeContext:
    def setup_method(self):
        _pending_skill_contexts.clear()

    def test_store_and_pop(self):
        ctx = SkillContext("msg", "sys", "user1")
        store_skill_resume_context("sys", "user1", "email_skill", ctx, [{"id": "step2"}])

        result = pop_skill_resume_context("sys", "user1")
        assert result is not None
        assert result["skill_name"] == "email_skill"
        assert len(result["remaining_steps"]) == 1

    def test_pop_removes_context(self):
        ctx = SkillContext("msg", "sys", "user1")
        store_skill_resume_context("sys", "user1", "skill", ctx, [])

        pop_skill_resume_context("sys", "user1")
        # Second pop should return None
        assert pop_skill_resume_context("sys", "user1") is None

    def test_pop_nonexistent_user(self):
        assert pop_skill_resume_context("sys", "nonexistent_user") is None

    def test_overwrite_previous_context(self):
        ctx1 = SkillContext("first", "sys", "user1")
        ctx2 = SkillContext("second", "sys", "user1")

        store_skill_resume_context("sys", "user1", "skill_a", ctx1, [])
        store_skill_resume_context("sys", "user1", "skill_b", ctx2, [])

        result = pop_skill_resume_context("sys", "user1")
        assert result["skill_name"] == "skill_b"

    def test_cross_system_isolation(self):
        """Pending contexts should NOT leak across systems (P0-3)."""
        ctx_a = SkillContext("msg", "system_a", "user1")
        ctx_b = SkillContext("msg", "system_b", "user1")

        store_skill_resume_context("system_a", "user1", "skill_a", ctx_a, [{"id": "s1"}])
        store_skill_resume_context("system_b", "user1", "skill_b", ctx_b, [{"id": "s2"}])

        # Pop from system_a should only get skill_a
        result_a = pop_skill_resume_context("system_a", "user1")
        assert result_a["skill_name"] == "skill_a"

        # Pop from system_b should get skill_b
        result_b = pop_skill_resume_context("system_b", "user1")
        assert result_b["skill_name"] == "skill_b"


# ---------------------------------------------------------------------------
# _process_step_result (shared logic P4-3)
# ---------------------------------------------------------------------------


class TestProcessStepResult:
    def test_stores_result_and_output_var(self):
        ctx = SkillContext("test", "s1", "u1")
        step = {"id": "step1", "output_var": "my_var"}
        _process_step_result(step, "step1", "some result", ctx)

        assert ctx.step_results["step1"] == "some result"
        assert ctx.variables["my_var"] == "some result"

    def test_extracts_json_variables(self):
        ctx = SkillContext("test", "s1", "u1")
        step = {"id": "search", "output_var": "results"}
        json_result = '[{"url": "https://example.com", "title": "Example", "description": "Desc"}]'
        _process_step_result(step, "search", json_result, ctx)

        assert ctx.variables["first_result_url"] == "https://example.com"
        assert ctx.variables["first_result_title"] == "Example"
        assert ctx.variables["result_count"] == "1"

    def test_no_json_no_extraction(self):
        ctx = SkillContext("test", "s1", "u1")
        step = {"id": "draft"}
        _process_step_result(step, "draft", "plain text response", ctx)

        assert ctx.step_results["draft"] == "plain text response"
        assert "first_result_url" not in ctx.variables


# ---------------------------------------------------------------------------
# v1 pipeline execution (mocked)
# ---------------------------------------------------------------------------


class TestV1Pipeline:
    @pytest.mark.asyncio
    async def test_v1_single_agent(self):
        """v1 skill with single agent pipeline."""
        skill = {
            "name": "simple_skill",
            "_version": 1,
            "pipeline": ["writer"],
        }
        with patch("realize_core.llm.router.route_to_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Generated blog post content"
            with patch("realize_core.llm.router.classify_task", return_value="content"):
                with patch("realize_core.prompt.builder.build_system_prompt", return_value="system prompt"):
                    from realize_core.skills.executor import _execute_v1_pipeline

                    result = await _execute_v1_pipeline(
                        skill, "write a blog post", "test", "user1",
                        None, None, None, "api",
                    )
                    assert "Generated blog post" in result

    @pytest.mark.asyncio
    async def test_v1_multi_agent_pipeline(self):
        """v1 skill with multi-agent pipeline passes previous outputs."""
        skill = {
            "name": "content_pipeline",
            "_version": 1,
            "pipeline": ["writer", "reviewer"],
        }
        call_count = 0

        async def mock_route(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Draft: AI is transforming business"
            return "APPROVED: Polished content ready"

        with patch("realize_core.llm.router.route_to_llm", side_effect=mock_route):
            with patch("realize_core.llm.router.classify_task", return_value="content"):
                with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt"):
                    from realize_core.skills.executor import _execute_v1_pipeline

                    result = await _execute_v1_pipeline(
                        skill, "write about AI", "test", "user1",
                        None, None, None, "api",
                    )
                    assert call_count == 2
                    assert "APPROVED" in result

    @pytest.mark.asyncio
    async def test_v1_empty_pipeline(self):
        """v1 skill with no pipeline defaults to orchestrator."""
        skill = {
            "name": "default_skill",
            "_version": 1,
            "pipeline": [],
        }
        with patch("realize_core.llm.router.route_to_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Response"
            with patch("realize_core.llm.router.classify_task", return_value="simple"):
                with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt"):
                    from realize_core.skills.executor import _execute_v1_pipeline

                    result = await _execute_v1_pipeline(
                        skill, "hello", "test", "user1",
                        None, None, None, "api",
                    )
                    # Empty pipeline should return the fallback message
                    assert result == "No output from pipeline."


# ---------------------------------------------------------------------------
# v2 step execution (mocked)
# ---------------------------------------------------------------------------


class TestV2Steps:
    @pytest.mark.asyncio
    async def test_v2_no_steps(self):
        """v2 skill with empty steps returns a message."""
        skill = {
            "name": "empty_skill",
            "_version": 2,
            "steps": [],
        }
        from realize_core.skills.executor import _execute_v2_steps

        result = await _execute_v2_steps(
            skill, "hello", "test", "user1",
            None, None, None, "api",
        )
        assert "no steps" in result.lower() or "no output" in result.lower()

    @pytest.mark.asyncio
    async def test_v2_agent_step(self):
        """v2 skill executing a single agent step."""
        skill = {
            "name": "agent_skill",
            "_version": 2,
            "steps": [
                {"id": "draft", "type": "agent", "agent": "writer"},
            ],
        }
        with patch("realize_core.llm.router.route_to_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Drafted content"
            with patch("realize_core.llm.router.classify_task", return_value="content"):
                with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt"):
                    with patch("realize_core.memory.conversation.get_history", return_value=[]):
                        from realize_core.skills.executor import _execute_v2_steps

                        result = await _execute_v2_steps(
                            skill, "write article", "test", "user1",
                            None, None, None, "api",
                        )
                        assert result == "Drafted content"

    @pytest.mark.asyncio
    async def test_v2_query_template_and_first_result_url(self):
        """Tool steps can derive query params and expose first_result_url to later steps."""
        skill = {
            "name": "research_skill",
            "_version": 2,
            "steps": [
                {
                    "id": "search",
                    "type": "tool",
                    "action": "web_search",
                    "query_template": "{user_message}",
                    "output_var": "search_results",
                },
                {
                    "id": "fetch",
                    "type": "tool",
                    "action": "web_fetch",
                    "params": {"url": "{first_result_url}"},
                },
            ],
        }

        mock_search = AsyncMock(
            return_value=[
                {
                    "title": "Market Update",
                    "url": "https://example.com/market-update",
                    "description": "Daily wrap",
                }
            ]
        )
        mock_fetch = AsyncMock(
            return_value={
                "url": "https://example.com/market-update",
                "title": "Market Update",
                "content": "Fetched page body",
                "truncated": False,
            }
        )

        with patch(
            "realize_core.skills.executor._get_tool_functions",
            return_value={"web_search": mock_search, "web_fetch": mock_fetch},
        ):
            from realize_core.skills.executor import _execute_v2_steps

            result = await _execute_v2_steps(
                skill, "today market recap", "test", "user1",
                None, None, None, "api",
            )

            mock_search.assert_awaited_once()
            mock_fetch.assert_awaited_once()
            assert "Fetched page body" in result

    @pytest.mark.asyncio
    async def test_agent_step_supports_extra_context_files(self):
        """Agent steps can pass extra context files into the prompt builder."""
        skill = {
            "name": "contextual_skill",
            "_version": 2,
            "steps": [
                {
                    "id": "draft",
                    "type": "agent",
                    "agent": "orchestrator",
                    "extra_context_files": ["systems/demo/F-foundations/investment-policy.md"],
                },
            ],
        }

        with patch("realize_core.llm.router.route_to_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Context-aware response"
            with patch("realize_core.llm.router.classify_task", return_value="content"):
                with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt") as mock_prompt:
                    with patch("realize_core.memory.conversation.get_history", return_value=[]):
                        from realize_core.skills.executor import _execute_v2_steps

                        result = await _execute_v2_steps(
                            skill, "review the policy", "demo", "user1",
                            None, None, None, "api",
                        )

                        assert result == "Context-aware response"
                        assert mock_prompt.call_args.kwargs["extra_context_files"] == [
                            "systems/demo/F-foundations/investment-policy.md"
                        ]


# ---------------------------------------------------------------------------
# Condition steps (P2-5 enhanced)
# ---------------------------------------------------------------------------


class TestConditionStep:
    @pytest.mark.asyncio
    async def test_condition_skip(self):
        from realize_core.skills.executor import SkillContext, _execute_condition_step

        step = {
            "type": "condition",
            "check": "{previous_result}",
            "branches": {
                "no": "skip",
                "yes": "continue",
            },
        }
        ctx = SkillContext("test", "s1", "u1")
        ctx.step_results["previous_result"] = "No, skip this"
        result = await _execute_condition_step(step, ctx)
        assert result == "__SKIP__"

    @pytest.mark.asyncio
    async def test_condition_stop(self):
        from realize_core.skills.executor import SkillContext, _execute_condition_step

        step = {
            "type": "condition",
            "check": "{check_val}",
            "branches": {
                "abort": "stop",
            },
        }
        ctx = SkillContext("test", "s1", "u1")
        ctx.step_results["check_val"] = "Must abort now"
        result = await _execute_condition_step(step, ctx)
        assert result == "__STOP__"

    @pytest.mark.asyncio
    async def test_condition_default_continue(self):
        from realize_core.skills.executor import SkillContext, _execute_condition_step

        step = {
            "type": "condition",
            "check": "{val}",
            "branches": {
                "nothing_matches": "skip",
                "default": "continue",
            },
        }
        ctx = SkillContext("test", "s1", "u1")
        ctx.step_results["val"] = "something else entirely"
        result = await _execute_condition_step(step, ctx)
        assert "continue" in result.lower()


class TestConditionOperators:
    """Tests for enhanced condition matching (P2-5)."""

    def test_exact_match(self):
        assert _match_condition("exact:no", "no") is True
        assert _match_condition("exact:no", "No") is True
        assert _match_condition("exact:no", "innovation") is False
        assert _match_condition("exact:no", "no way") is False

    def test_startswith(self):
        assert _match_condition("startswith:error", "Error: something broke") is True
        assert _match_condition("startswith:error", "no error here") is False

    def test_regex(self):
        assert _match_condition("regex:score.*\\d+", "the score is 85") is True
        assert _match_condition("regex:^APPROVED", "APPROVED with notes") is True
        assert _match_condition("regex:^APPROVED", "Not APPROVED") is False

    def test_numeric_gt(self):
        assert _match_condition("gt:80", "Quality score: 85") is True
        assert _match_condition("gt:80", "Quality score: 75") is False

    def test_numeric_lt(self):
        assert _match_condition("lt:60", "Score is 45") is True
        assert _match_condition("lt:60", "Score is 65") is False

    def test_numeric_gte_lte(self):
        assert _match_condition("gte:80", "Score: 80") is True
        assert _match_condition("lte:60", "Score: 60") is True

    def test_word_boundary_default(self):
        """Default matching should use word boundaries (P2-5 fix)."""
        assert _match_condition("no", "no, skip this") is True
        assert _match_condition("no", "innovation is key") is False
        assert _match_condition("skip", "skip this step") is True
        assert _match_condition("skip", "skipping ahead") is False


# ---------------------------------------------------------------------------
# Human-in-the-loop steps
# ---------------------------------------------------------------------------


class TestHumanStep:
    @pytest.mark.asyncio
    async def test_human_step_returns_question(self):
        from realize_core.skills.executor import SkillContext, _execute_human_step

        step = {
            "type": "human",
            "question": "Should I send this email?",
        }
        ctx = SkillContext("test", "s1", "u1")
        result = await _execute_human_step(step, ctx)
        assert "__HUMAN_INPUT_NEEDED__" in result
        assert "send this email" in result

    @pytest.mark.asyncio
    async def test_human_step_injects_variables(self):
        from realize_core.skills.executor import SkillContext, _execute_human_step

        step = {
            "type": "human",
            "question": "Send email about {user_message}?",
        }
        ctx = SkillContext("meeting tomorrow", "s1", "u1")
        result = await _execute_human_step(step, ctx)
        assert "meeting tomorrow" in result


# ---------------------------------------------------------------------------
# Step error isolation (P2-2)
# ---------------------------------------------------------------------------


class TestStepErrorIsolation:
    @pytest.mark.asyncio
    async def test_step_failure_continues_by_default(self):
        """When a step fails, execution should continue (on_error=continue default)."""
        skill = {
            "name": "error_skill",
            "_version": 2,
            "steps": [
                {"id": "failing_step", "type": "tool", "action": "nonexistent_tool"},
                {"id": "good_step", "type": "agent", "agent": "writer"},
            ],
        }
        with patch(
            "realize_core.skills.executor._get_tool_functions",
            return_value={},  # Empty — tool not found
        ):
            with patch("realize_core.llm.router.route_to_llm", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = "Good output"
                with patch("realize_core.llm.router.classify_task", return_value="content"):
                    with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt"):
                        with patch("realize_core.memory.conversation.get_history", return_value=[]):
                            from realize_core.skills.executor import _execute_v2_steps

                            result = await _execute_v2_steps(
                                skill, "test", "sys", "user1",
                                None, None, None, "api",
                            )
                            # The good step should still execute
                            assert result == "Good output"

    @pytest.mark.asyncio
    async def test_step_failure_stops_when_configured(self):
        """When on_error=stop, a step that raises should halt execution."""
        skill = {
            "name": "stop_on_error",
            "_version": 2,
            "steps": [
                {"id": "failing_step", "type": "agent", "agent": "writer", "on_error": "stop"},
                {"id": "never_reached", "type": "agent", "agent": "reviewer"},
            ],
        }
        call_count = 0

        async def mock_route(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM provider unavailable")
            return "Should not reach"

        with patch("realize_core.llm.router.route_to_llm", side_effect=mock_route):
            with patch("realize_core.llm.router.classify_task", return_value="content"):
                with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt"):
                    with patch("realize_core.memory.conversation.get_history", return_value=[]):
                        from realize_core.skills.executor import _execute_v2_steps

                        result = await _execute_v2_steps(
                            skill, "test", "sys", "user1",
                            None, None, None, "api",
                        )
                        # Only the failing step should have been attempted
                        assert call_count == 1
                        # Should have the error message from the failing step
                        assert "failed" in result.lower()


# ---------------------------------------------------------------------------
# Agent step uses route_to_llm (P2-3)
# ---------------------------------------------------------------------------


class TestAgentStepUsesRouter:
    @pytest.mark.asyncio
    async def test_agent_step_calls_route_to_llm(self):
        """Agent steps should use route_to_llm, not call_claude."""
        from realize_core.skills.executor import SkillContext, _execute_agent_step

        ctx = SkillContext("write something", "test", "user1")

        with patch("realize_core.llm.router.route_to_llm", new_callable=AsyncMock) as mock_router:
            mock_router.return_value = "Routed response"
            with patch("realize_core.llm.router.classify_task", return_value="content"):
                with patch("realize_core.memory.conversation.get_history", return_value=[]):
                    with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt"):
                        result = await _execute_agent_step(
                            {"id": "step1", "type": "agent", "agent": "writer"},
                            ctx, None, None, None, "api",
                        )
                        mock_router.assert_awaited_once()
                        assert result == "Routed response"


# ---------------------------------------------------------------------------
# Lazy tool registry (P2-4)
# ---------------------------------------------------------------------------


class TestToolRegistryLazy:
    def test_registry_caches_result(self):
        """Tool functions should be loaded once and cached."""
        import realize_core.skills.executor as executor

        # Reset cache
        executor._tool_functions = None

        with patch("builtins.__import__", side_effect=ImportError("test")):
            funcs1 = executor._get_tool_functions()
            funcs2 = executor._get_tool_functions()
            # Should be the same object (cached)
            assert funcs1 is funcs2

        # Clean up
        executor._tool_functions = None


# ---------------------------------------------------------------------------
# Dry-run mode (P3-3)
# ---------------------------------------------------------------------------


class TestDryRunMode:
    @pytest.mark.asyncio
    async def test_dry_run_returns_plan_v1(self):
        """Dry-run for v1 should return pipeline plan without executing."""
        skill = {
            "name": "test_skill",
            "_version": 1,
            "pipeline": ["writer", "reviewer"],
            "task_type": "content",
        }
        result = await execute_skill(
            skill, "write post", "test", "user1", dry_run=True,
        )
        assert isinstance(result, dict)
        assert result["skill_name"] == "test_skill"
        assert result["version"] == 1
        assert result["pipeline"] == ["writer", "reviewer"]
        assert result["would_execute"] is True

    @pytest.mark.asyncio
    async def test_dry_run_returns_plan_v2(self):
        """Dry-run for v2 should return step descriptions without executing."""
        skill = {
            "name": "v2_skill",
            "_version": 2,
            "steps": [
                {"id": "search", "type": "tool", "action": "web_search"},
                {"id": "analyze", "type": "agent", "agent": "analyst"},
            ],
        }
        result = await execute_skill(
            skill, "research AI", "test", "user1", dry_run=True,
        )
        assert isinstance(result, dict)
        assert result["skill_name"] == "v2_skill"
        assert result["version"] == 2
        assert len(result["steps"]) == 2
        assert result["steps"][0]["id"] == "search"
        assert result["steps"][0]["type"] == "tool"


# ---------------------------------------------------------------------------
# Execution audit log (P3-2)
# ---------------------------------------------------------------------------


class TestExecutionLog:
    @pytest.mark.asyncio
    async def test_execution_creates_log(self):
        """Skill execution should produce a SkillExecutionLog."""
        skill = {
            "name": "logged_skill",
            "_version": 1,
            "pipeline": ["writer"],
        }

        persisted_logs = []

        def mock_persist(self):
            persisted_logs.append(self)

        with patch("realize_core.llm.router.route_to_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Response"
            with patch("realize_core.llm.router.classify_task", return_value="content"):
                with patch("realize_core.prompt.builder.build_system_prompt", return_value="prompt"):
                    with patch.object(SkillExecutionLog, "persist", mock_persist):
                        await execute_skill(
                            skill, "test", "sys", "user1",
                            None, None, None, "api",
                        )

        assert len(persisted_logs) == 1
        log = persisted_logs[0]
        assert log.skill_name == "logged_skill"
        assert log.version == 1
        assert log.system_key == "sys"
        assert log.outcome == "success"
        assert log.steps_executed == 1


# ---------------------------------------------------------------------------
# execute_skill dispatcher
# ---------------------------------------------------------------------------


class TestExecuteSkill:
    @pytest.mark.asyncio
    async def test_dispatches_to_v1(self):
        skill = {"name": "test", "_version": 1, "pipeline": ["writer"]}
        with patch("realize_core.skills.executor._execute_v1_pipeline", new_callable=AsyncMock) as mock:
            mock.return_value = "v1 result"
            with patch.object(SkillExecutionLog, "persist"):
                result = await execute_skill(skill, "msg", "sys", "u1")
                mock.assert_called_once()
                assert result == "v1 result"

    @pytest.mark.asyncio
    async def test_dispatches_to_v2(self):
        skill = {"name": "test", "_version": 2, "steps": []}
        with patch("realize_core.skills.executor._execute_v2_steps", new_callable=AsyncMock) as mock:
            mock.return_value = "v2 result"
            with patch.object(SkillExecutionLog, "persist"):
                result = await execute_skill(skill, "msg", "sys", "u1")
                mock.assert_called_once()
                assert result == "v2 result"

    @pytest.mark.asyncio
    async def test_default_version_is_v1(self):
        """Skills without _version should default to v1."""
        skill = {"name": "test", "pipeline": ["writer"]}
        with patch("realize_core.skills.executor._execute_v1_pipeline", new_callable=AsyncMock) as mock:
            mock.return_value = "v1 default"
            with patch.object(SkillExecutionLog, "persist"):
                await execute_skill(skill, "msg", "sys", "u1")
                mock.assert_called_once()
