"""
Skill Executor Engine for RealizeOS: Multi-step workflow runner.

Supports composable, tool-aware workflows with step types:
- agent  — Call an LLM agent with context injection
- tool   — Execute a web/Google/browser tool directly
- condition — Branch based on a previous step's result
- human  — Ask the user for input/confirmation before proceeding

Each step's result feeds into the next step's context.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pending skill contexts — keyed by (system_key, user_id) to prevent
# cross-venture leakage (P0-3 fix)
# ---------------------------------------------------------------------------

_pending_skill_contexts: dict[tuple[str, str], dict] = {}


def store_skill_resume_context(
    system_key: str, user_id: str, skill_name: str, ctx, remaining_steps: list
):
    """Store skill context for resumption after user confirms an action."""
    _pending_skill_contexts[(system_key, user_id)] = {
        "skill_name": skill_name,
        "context": ctx,
        "remaining_steps": remaining_steps,
    }
    logger.info(
        f"Stored skill resume context for user {user_id} in {system_key}, "
        f"skill={skill_name}, {len(remaining_steps)} steps remaining"
    )


def pop_skill_resume_context(system_key: str, user_id: str) -> dict | None:
    """Pop and return the stored skill context for a user in a system, if any."""
    return _pending_skill_contexts.pop((system_key, user_id), None)


# ---------------------------------------------------------------------------
# Skill context
# ---------------------------------------------------------------------------


class SkillContext:
    """Holds accumulated context across skill steps."""

    def __init__(self, user_message: str, system_key: str, user_id: str):
        self.user_message = user_message
        self.system_key = system_key
        self.user_id = user_id
        self.step_results: dict[str, str] = {}
        self.variables: dict[str, str] = {"doc_title": user_message}
        self.progress_messages: list[str] = []
        self.annotations: dict[str, dict] = {}

    def inject(self, template: str) -> str:
        """Replace {variable} placeholders in a template string."""
        result = template
        for step_id, value in self.step_results.items():
            result = result.replace(f"{{{step_id}}}", str(value))
        for var, value in self.variables.items():
            result = result.replace(f"{{{var}}}", str(value))
        result = result.replace("{user_message}", self.user_message)
        result = result.replace("{today}", date.today().isoformat())
        return result


# ---------------------------------------------------------------------------
# Skill execution audit log (P3-2)
# ---------------------------------------------------------------------------


@dataclass
class SkillExecutionLog:
    """Structured record of a skill execution for auditing."""

    skill_name: str
    version: int
    system_key: str
    user_id: str
    started_at: str
    completed_at: str = ""
    steps_executed: int = 0
    steps_failed: int = 0
    outcome: str = ""  # "success", "partial", "failed", "paused"
    step_timings: list[dict] = field(default_factory=list)

    def persist(self):
        """Persist to SQLite via the shared memory store."""
        try:
            from realize_core.memory.store import db_connection

            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO skill_execution_logs "
                    "(skill_name, version, system_key, user_id, started_at, completed_at, "
                    "steps_executed, steps_failed, outcome, step_timings) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.skill_name,
                        self.version,
                        self.system_key,
                        self.user_id,
                        self.started_at,
                        self.completed_at,
                        self.steps_executed,
                        self.steps_failed,
                        self.outcome,
                        json.dumps(self.step_timings),
                    ),
                )
        except Exception as e:
            logger.debug(f"Failed to persist skill execution log: {e}")


# ---------------------------------------------------------------------------
# JSON result parsing and variable extraction
# ---------------------------------------------------------------------------


def _parse_json_result(result: str):
    """Best-effort JSON parsing for tool results serialized to text."""
    if not isinstance(result, str):
        return None
    try:
        return json.loads(result)
    except (TypeError, json.JSONDecodeError):
        pass
    # Try extracting a JSON object from mixed text (e.g., agent output with surrounding prose)
    match = re.search(r"\{[^{}]*\}", result)
    if match:
        try:
            return json.loads(match.group())
        except (TypeError, json.JSONDecodeError):
            pass
    return None


def _extract_common_variables(parsed, ctx: SkillContext):
    """Expose common tool-result fields as reusable variables for later steps."""
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        first = parsed[0]
        if "url" in first:
            ctx.variables["first_result_url"] = str(first["url"])
        if "title" in first:
            ctx.variables["first_result_title"] = str(first["title"])
        if "description" in first:
            ctx.variables["first_result_description"] = str(first["description"])
        ctx.variables["result_count"] = str(len(parsed))
    elif isinstance(parsed, dict):
        for key, value in parsed.items():
            ctx.variables[key] = str(value)


def _process_step_result(step: dict, step_id: str, result: str, ctx: SkillContext):
    """Record a step result and extract variables — shared by execute and resume paths."""
    ctx.step_results[step_id] = result
    output_var = step.get("output_var")
    if output_var:
        ctx.variables[output_var] = result

    parsed = _parse_json_result(result)
    if parsed is not None:
        ctx.annotations[step_id] = {"parsed": parsed}
        if output_var:
            ctx.annotations[output_var] = {"parsed": parsed}
        _extract_common_variables(parsed, ctx)


# ---------------------------------------------------------------------------
# Lazy tool registry (P2-4 — built once, not per step)
# ---------------------------------------------------------------------------

_tool_functions: dict[str, object] | None = None


def _get_tool_functions() -> dict[str, object]:
    """Build and cache the tool function map from all registered tool modules."""
    global _tool_functions
    if _tool_functions is not None:
        return _tool_functions

    funcs: dict[str, object] = {}
    _tool_modules = [
        ("realize_core.tools.web", "TOOL_FUNCTIONS"),
        ("realize_core.tools.google_workspace", "TOOL_FUNCTIONS"),
        ("realize_core.tools.kb_tools", "TOOL_FUNCTIONS"),
        ("realize_core.tools.voice_tools", "TOOL_FUNCTIONS"),
    ]
    for module_path, var_name in _tool_modules:
        try:
            mod = __import__(module_path, fromlist=[var_name])
            funcs.update(getattr(mod, var_name))
        except (ImportError, AttributeError) as e:
            logger.debug(f"Tool module {module_path} not available: {e}")

    _tool_functions = funcs
    return _tool_functions


# ---------------------------------------------------------------------------
# Condition matching (P2-5 — enhanced evaluation with operators)
# ---------------------------------------------------------------------------


def _match_condition(pattern: str, value: str) -> bool:
    """Match a condition pattern against a value.

    Supported patterns:
    - "exact:text"      — exact case-insensitive match
    - "startswith:prefix" — starts with prefix
    - "regex:pattern"   — regex match
    - "gt:N" / "lt:N" / "gte:N" / "lte:N" — numeric comparison
    - plain string      — word-boundary-aware contains (default, backward-compatible)
    """
    if ":" in pattern:
        parts = pattern.split(":", 1)
        op = parts[0].lower()
        operand = parts[1]

        if op == "exact":
            return operand.lower() == value.lower()
        elif op == "startswith":
            return value.lower().startswith(operand.lower())
        elif op == "regex":
            return bool(re.search(operand, value, re.IGNORECASE))
        elif op in ("gt", "lt", "gte", "lte"):
            try:
                nums = re.findall(r"-?\d+\.?\d*", value)
                if nums:
                    val = float(nums[0])
                    threshold = float(operand)
                    ops = {"gt": val > threshold, "lt": val < threshold,
                           "gte": val >= threshold, "lte": val <= threshold}
                    return ops[op]
            except ValueError:
                pass
            return False

    # Default: word-boundary-aware contains (fixes "no" matching "innovation")
    escaped = re.escape(pattern.lower())
    return bool(re.search(r"\b" + escaped + r"\b", value.lower()))


# ---------------------------------------------------------------------------
# Dry-run mode (P3-3)
# ---------------------------------------------------------------------------


def _build_dry_run_plan(skill: dict) -> dict:
    """Build a dry-run execution plan describing what would happen."""
    skill_name = skill.get("name", "unnamed")
    version = skill.get("_version", 1)

    plan: dict = {
        "skill_name": skill_name,
        "version": version,
        "would_execute": True,
    }

    if version == 1:
        plan["pipeline"] = skill.get("pipeline", ["orchestrator"])
        plan["task_type"] = skill.get("task_type", "general")
        plan["steps"] = [
            {"agent": agent, "type": "agent"} for agent in plan["pipeline"]
        ]
    else:
        steps = skill.get("steps", [])
        plan["steps"] = [
            {
                "id": s.get("id", f"step_{i}"),
                "type": s.get("type", "agent"),
                "agent": s.get("agent"),
                "tool": s.get("action", s.get("tool")),
                "has_condition": "condition" in s,
                "on_error": s.get("on_error", "continue"),
            }
            for i, s in enumerate(steps)
        ]

    return plan


# ---------------------------------------------------------------------------
# Main execution entry point
# ---------------------------------------------------------------------------


async def execute_skill(
    skill: dict,
    user_message: str,
    system_key: str,
    user_id: str,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    channel: str = "api",
    dry_run: bool = False,
) -> str | dict:
    """
    Execute a skill (v1 pipeline or v2 multi-step workflow).

    Args:
        skill: Skill definition dict (from detector)
        user_message: The user's message that triggered the skill
        system_key: Active system key
        user_id: User identifier
        kb_path: Knowledge base root path
        system_config: System configuration dict
        shared_config: Shared config (identity, preferences paths)
        channel: Channel for format instructions
        dry_run: If True, return execution plan without calling LLM/tools

    Returns:
        Skill execution result text, or dict (if dry_run=True)
    """
    skill_name = skill.get("name", "unnamed")
    version = skill.get("_version", 1)

    if dry_run:
        return _build_dry_run_plan(skill)

    logger.info(f"Executing skill: {skill_name} (v{version}) for system={system_key}")

    # Start audit log
    exec_log = SkillExecutionLog(
        skill_name=skill_name,
        version=version,
        system_key=system_key,
        user_id=user_id,
        started_at=datetime.now().isoformat(),
    )

    try:
        if version == 1:
            result = await _execute_v1_pipeline(
                skill, user_message, system_key, user_id,
                kb_path, system_config, shared_config, channel,
                exec_log=exec_log,
            )
        else:
            result = await _execute_v2_steps(
                skill, user_message, system_key, user_id,
                kb_path, system_config, shared_config, channel,
                exec_log=exec_log,
            )

        exec_log.outcome = "success" if exec_log.steps_failed == 0 else "partial"
    except Exception as e:
        exec_log.outcome = "failed"
        logger.error(f"Skill execution failed: {skill_name}: {e}", exc_info=True)
        result = f"Skill '{skill_name}' failed: {str(e)[:300]}"
    finally:
        exec_log.completed_at = datetime.now().isoformat()
        exec_log.persist()

    return result


# ---------------------------------------------------------------------------
# V1 pipeline execution
# ---------------------------------------------------------------------------


async def _execute_v1_pipeline(
    skill: dict,
    user_message: str,
    system_key: str,
    user_id: str,
    kb_path,
    system_config,
    shared_config,
    channel,
    exec_log: SkillExecutionLog = None,
) -> str:
    """Execute a v1 skill (trigger -> agent pipeline)."""
    from realize_core.llm.router import classify_task, route_to_llm
    from realize_core.prompt.builder import build_system_prompt

    pipeline = skill.get("pipeline", ["orchestrator"])
    task_type = skill.get("task_type", classify_task(user_message, system_key=system_key))
    results = []

    for i, agent_key in enumerate(pipeline):
        step_start = datetime.now()

        # Build prompt for this agent
        system_prompt = build_system_prompt(
            kb_path=kb_path,
            system_config=system_config or {},
            system_key=system_key,
            agent_key=agent_key,
            user_message=user_message,
            shared_config=shared_config,
            channel=channel,
        )

        # Build message with context from previous agents
        if results:
            context = "\n\n".join([f"## Previous agent output\n{r}" for r in results])
            message_content = f"{context}\n\n## User request\n{user_message}"
        else:
            message_content = user_message

        messages = [{"role": "user", "content": message_content}]

        response = await route_to_llm(
            system_prompt=system_prompt,
            messages=messages,
            task_type=task_type,
            system_key=system_key,
        )
        results.append(response)

        if exec_log:
            exec_log.steps_executed += 1
            exec_log.step_timings.append({
                "step": agent_key,
                "type": "agent",
                "duration_ms": int((datetime.now() - step_start).total_seconds() * 1000),
            })

        logger.info(f"Pipeline step {i + 1}/{len(pipeline)}: {agent_key} completed")

    return results[-1] if results else "No output from pipeline."


# ---------------------------------------------------------------------------
# V2 multi-step execution
# ---------------------------------------------------------------------------


async def _execute_v2_steps(
    skill: dict,
    user_message: str,
    system_key: str,
    user_id: str,
    kb_path,
    system_config,
    shared_config,
    channel,
    exec_log: SkillExecutionLog = None,
) -> str:
    """Execute a v2 skill (multi-step workflow)."""
    steps = skill.get("steps", [])
    if not steps:
        return "Skill has no steps defined."

    ctx = SkillContext(user_message, system_key, user_id)

    outputs, human_question = await run_steps(
        steps=steps,
        ctx=ctx,
        kb_path=kb_path,
        system_config=system_config,
        shared_config=shared_config,
        channel=channel,
        skill_name=skill.get("name", ""),
        exec_log=exec_log,
    )

    if human_question is not None:
        return human_question

    return outputs[-1] if outputs else "Skill completed with no output."


async def run_steps(
    steps: list[dict],
    ctx: SkillContext,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    channel: str = "api",
    skill_name: str = "",
    exec_log: SkillExecutionLog = None,
) -> tuple[list[str], str | None]:
    """Execute a list of skill steps.

    Shared by both initial v2 execution and HITL resume paths (P3-4/P4-3).

    Returns:
        (outputs, human_question) — human_question is set if a HITL step paused execution.
    """
    outputs: list[str] = []

    for i, step in enumerate(steps):
        step_id = step.get("id", f"step_{i}")
        step_type = step.get("type", "agent")
        step_start = datetime.now()

        logger.info(f"Executing step {i + 1}/{len(steps)}: {step_id} ({step_type})")

        # Check inline condition for conditional steps
        condition = step.get("condition")
        if condition:
            condition_value = ctx.inject(condition)
            if re.search(r"\b(no|skip)\b", condition_value.lower()):
                logger.info(f"Skipping step {step_id} (condition not met)")
                continue

        # Execute step with error isolation (P2-2)
        try:
            if step_type == "agent":
                result = await _execute_agent_step(
                    step, ctx, kb_path, system_config, shared_config, channel,
                )
            elif step_type == "tool":
                result = await _execute_tool_step(step, ctx)
            elif step_type == "condition":
                result = await _execute_condition_step(step, ctx)
                if result == "__SKIP__":
                    continue
                elif result == "__STOP__":
                    break
            elif step_type == "human":
                result = await _execute_human_step(step, ctx)
                if result.startswith("__HUMAN_INPUT_NEEDED__"):
                    # Store context for resumption (P0-3: keyed by system_key + user_id)
                    remaining = steps[i + 1:]
                    store_skill_resume_context(
                        ctx.system_key, ctx.user_id, skill_name, ctx, remaining,
                    )
                    if exec_log:
                        exec_log.outcome = "paused"
                        exec_log.steps_executed += 1
                    return outputs, result.replace("__HUMAN_INPUT_NEEDED__\n", "")
            else:
                result = f"Unknown step type: {step_type}"
        except Exception as e:
            logger.error(f"Step {step_id} failed: {e}", exc_info=True)
            on_error = step.get("on_error", "continue")
            result = f"Step {step_id} failed: {str(e)[:200]}"
            if exec_log:
                exec_log.steps_failed += 1
            if on_error == "stop":
                _process_step_result(step, step_id, result, ctx)
                outputs.append(result)
                break

        # Record result and extract variables (shared logic — P4-3)
        _process_step_result(step, step_id, result, ctx)
        outputs.append(result)

        if exec_log:
            exec_log.steps_executed += 1
            exec_log.step_timings.append({
                "step": step_id,
                "type": step_type,
                "duration_ms": int((datetime.now() - step_start).total_seconds() * 1000),
            })

        ctx.progress_messages.append(f"Step {i + 1}/{len(steps)} ({step_id}): done")

    return outputs, None


# ---------------------------------------------------------------------------
# Step type implementations
# ---------------------------------------------------------------------------


async def _execute_agent_step(step, ctx, kb_path, system_config, shared_config, channel) -> str:
    """Execute an agent step: call an LLM agent via the multi-LLM router (P2-3)."""
    from realize_core.llm.router import classify_task, route_to_llm
    from realize_core.memory.conversation import get_history
    from realize_core.prompt.builder import build_system_prompt

    agent_key = step.get("agent", "orchestrator")
    inject_context = step.get("inject_context", [])
    custom_prompt = step.get("prompt") or step.get("instructions")
    extra_context_files = step.get("extra_context_files", [])

    system_prompt = build_system_prompt(
        kb_path=kb_path,
        system_config=system_config or {},
        system_key=ctx.system_key,
        agent_key=agent_key,
        extra_context_files=extra_context_files,
        shared_config=shared_config,
        channel=channel,
    )

    parts = []

    # Include recent conversation history so the agent has multi-turn context
    history = get_history(ctx.system_key, ctx.user_id, limit=10)
    if history:
        history_lines = []
        for msg in history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:800]
            history_lines.append(f"**{role}**: {content}")
        parts.append("## Recent conversation context\n" + "\n\n".join(history_lines) + "\n")

    if inject_context:
        parts.append("## Context from previous steps\n")
        for ref in inject_context:
            if ref in ctx.step_results:
                parts.append(f"### {ref}\n{ctx.step_results[ref]}\n")
            elif ref in ctx.variables:
                parts.append(f"### {ref}\n{ctx.variables[ref]}\n")

    if custom_prompt:
        parts.append(ctx.inject(custom_prompt))
    else:
        parts.append(ctx.user_message)

    if step.get("review"):
        latest_output = list(ctx.step_results.values())[-1] if ctx.step_results else ""
        parts.append(f"\n\nPlease review this output:\n{latest_output}")

    assembled = "\n\n".join(parts)
    messages = [{"role": "user", "content": assembled}]

    # Route through LLM router (P2-3) — enables multi-LLM, fallback chains, cost optimization
    task_type = step.get("task_type") or classify_task(ctx.user_message, system_key=ctx.system_key)
    return await route_to_llm(
        system_prompt=system_prompt,
        messages=messages,
        task_type=task_type,
        system_key=ctx.system_key,
    )


async def _execute_tool_step(step, ctx) -> str:
    """Execute a tool step: call a registered tool function."""
    tool_name = step.get("action", step.get("tool"))
    if not tool_name:
        return "Error: no tool specified in step"

    raw_params = step.get("params", {})
    params = {}
    for key, value in raw_params.items():
        params[key] = ctx.inject(str(value)) if isinstance(value, str) else value

    query_template = step.get("query_template")
    if query_template and "query" not in params:
        params["query"] = ctx.inject(query_template)

    # Use lazy tool registry (P2-4)
    all_funcs = _get_tool_functions()

    func = all_funcs.get(tool_name)
    if not func:
        return f"Error: unknown tool '{tool_name}'"

    try:
        result = await func(**params)
        result_str = json.dumps(result, indent=2, default=str, ensure_ascii=False)
        if len(result_str) > 6000:
            result_str = result_str[:6000] + "\n... (truncated)"
        return result_str
    except Exception as e:
        logger.error(f"Tool step error ({tool_name}): {e}", exc_info=True)
        return f"Error executing {tool_name}: {str(e)[:300]}"


async def _execute_condition_step(step, ctx) -> str:
    """Execute a condition step: branch based on previous results (P2-5 enhanced)."""
    check = step.get("check", "")
    check_value = ctx.inject(check) if check else ""

    branches = step.get("branches", {})
    matched_branch = None

    for pattern, branch_action in branches.items():
        if pattern == "default":
            continue
        if _match_condition(pattern, check_value):
            matched_branch = branch_action
            break

    if not matched_branch:
        matched_branch = branches.get("default", "continue")

    if matched_branch == "skip":
        return "__SKIP__"
    elif matched_branch == "stop":
        return "__STOP__"

    return f"Condition evaluated: matched '{matched_branch}'"


async def _execute_human_step(step, ctx) -> str:
    """Execute a human-in-the-loop step. Returns question for the user."""
    question = step.get("question", step.get("prompt", "Please confirm to continue."))
    question = ctx.inject(question)
    return f"__HUMAN_INPUT_NEEDED__\n{question}"
