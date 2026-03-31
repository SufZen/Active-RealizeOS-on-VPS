"""
Base Handler: The core message processing pipeline for RealizeOS.

Provides composable building blocks for handling incoming messages across
any channel (API, Telegram, Slack, etc.). Each channel adapter calls these
shared functions to process messages through the standard flow.
"""

import logging

from realize_core.llm.router import classify_task, route_to_llm
from realize_core.memory.conversation import add_message, get_history
from realize_core.pipeline.creative import (
    execute_pipeline_step,
)
from realize_core.pipeline.session import CreativeSession, get_session
from realize_core.prompt.builder import build_system_prompt

logger = logging.getLogger(__name__)

# Analytics imports (non-blocking — graceful if evolution module unavailable)
try:
    from realize_core.evolution.analytics import log_satisfaction
    from realize_core.evolution.tracker import InteractionTimer, detect_satisfaction_signal

    _analytics_available = True
except ImportError:
    _analytics_available = False

# Evolution handler imports (KB learning from conversations)
try:
    from realize_core.evolution.handler import analyze_evolution_intent, has_evolution_intent

    _evolution_available = True
except ImportError:
    _evolution_available = False

# Knowledge-question prefixes (skip skill detection for these)
INFO_PREFIXES = (
    "summarize",
    "explain",
    "what is",
    "what are",
    "describe",
    "tell me about",
    "how does",
    "how do",
    "overview of",
    "define",
)


def select_agent(agent_routing: dict, message: str, default: str = "orchestrator") -> str:
    """Select the best agent based on keyword scoring with ambiguity detection.

    When the top two agents score within 1 point of each other, the selection
    is ambiguous. In that case, falls back to the orchestrator which can
    delegate appropriately based on full context.
    """
    msg_lower = message.lower()
    scores = {}
    for agent, keywords in agent_routing.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > 0:
            scores[agent] = score
    if not scores:
        return default

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    best_agent, best_score = ranked[0]

    # If scores are ambiguous (top 2 within 1 point), prefer orchestrator
    # to delegate with full context rather than risk wrong agent
    if len(ranked) >= 2:
        second_agent, second_score = ranked[1]
        if best_score - second_score <= 1 and best_score <= 2:
            logger.debug(
                f"Ambiguous agent selection: {best_agent}={best_score} vs {second_agent}={second_score}, "
                f"delegating to orchestrator"
            )
            return default

    return best_agent


async def check_and_execute_skill(
    system_key: str,
    user_id: str,
    message: str,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    channel: str = "api",
) -> tuple[bool, str | None]:
    """
    Check for skill auto-trigger and execute if found.

    Also resumes paused skills (from human-in-the-loop steps) when the user
    sends a follow-up message after a skill was suspended awaiting confirmation.

    Returns (handled, result) where handled=True means the caller should
    use result as the response.
    """
    from realize_core.skills.executor import execute_skill, pop_skill_resume_context, run_steps

    # Check for pending skill awaiting user confirmation (human-in-the-loop resume)
    # P0-3: keyed by (system_key, user_id) to prevent cross-venture leakage
    pending = pop_skill_resume_context(system_key, user_id)
    if pending:
        skill_name = pending["skill_name"]
        ctx = pending["context"]
        remaining_steps = pending["remaining_steps"]
        logger.info(f"Resuming paused skill '{skill_name}' with user confirmation for {user_id}")

        # Inject user's reply as the approval/input for the next step
        ctx.variables["user_confirmation"] = message
        ctx.variables["approval"] = message

        # Resume execution from remaining steps using shared step runner (P4-3)
        outputs, human_question = await run_steps(
            steps=remaining_steps,
            ctx=ctx,
            kb_path=kb_path,
            system_config=system_config,
            shared_config=shared_config,
            channel=channel,
            skill_name=skill_name,
        )
        result = human_question if human_question is not None else (outputs[-1] if outputs else None)
        if result is not None:
            add_message(system_key, user_id, "user", message)
            add_message(system_key, user_id, "assistant", result)
            return True, result

    from realize_core.skills.detector import detect_skill

    skill = detect_skill(message, system_key, kb_path=kb_path)

    msg_lower = message.lower().strip()
    is_knowledge_question = any(msg_lower.startswith(p) for p in INFO_PREFIXES)

    if not skill or (is_knowledge_question and skill.get("_version", 1) == 1):
        return False, None

    logger.info(f"Skill triggered: {skill.get('name', 'unnamed')} for {system_key}")
    result = await execute_skill(
        skill=skill,
        user_message=message,
        system_key=system_key,
        user_id=user_id,
        kb_path=kb_path,
        system_config=system_config,
        shared_config=shared_config,
        channel=channel,
    )

    if result is not None:
        add_message(system_key, user_id, "user", message)
        add_message(system_key, user_id, "assistant", result)
        return True, result

    return False, None


async def standard_llm_handling(
    system_key: str,
    agent_key: str,
    user_id: str,
    message: str,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    extra_context_files: list[str] = None,
    channel: str = "api",
    features: dict = None,
    all_systems: dict = None,
) -> str:
    """
    Standard single-agent LLM handling: build prompt, classify, route, respond.

    This is the main message processing function for non-skill, non-session messages.
    """
    system_prompt = build_system_prompt(
        kb_path=kb_path,
        system_config=system_config or {},
        system_key=system_key,
        agent_key=agent_key,
        user_message=message,
        extra_context_files=extra_context_files,
        shared_config=shared_config,
        channel=channel,
        features=features,
        all_systems=all_systems,
    )

    history = get_history(system_key, user_id)
    add_message(system_key, user_id, "user", message)
    messages = history + [{"role": "user", "content": message}]

    task_class = classify_task(message, system_key=system_key)
    response = await route_to_llm(
        system_prompt, messages, task_class,
        system_key=system_key,
        conversation_depth=len(history),
    )

    add_message(system_key, user_id, "assistant", response)
    return response


async def handle_session_message(
    session: CreativeSession,
    user_id: str,
    message: str,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    extra_context_files: list[str] = None,
    channel: str = "api",
) -> str:
    """Handle a message within an active creative session."""
    response = await execute_pipeline_step(
        session=session,
        user_id=user_id,
        message=message,
        kb_path=kb_path,
        system_config=system_config,
        shared_config=shared_config,
        extra_context_files=extra_context_files,
        channel=channel,
    )

    # Only advance stage for substantive messages, not questions/clarifications (P3-1)
    msg_stripped = message.strip().lower()
    _question_starts = ("can you", "could you", "what", "how", "why", "when", "where", "who", "which", "is it", "are there")
    is_question = msg_stripped.endswith("?") or msg_stripped.startswith(_question_starts)

    if session.stage == "briefing" and not is_question:
        session.stage = "drafting"
        session.save()
    elif session.stage == "drafting" and not is_question:
        session.stage = "iterating"
        session.save()

    response += f"\n\n{session.summary()}"
    return response


async def handle_review(
    system_key: str,
    user_id: str,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    reviewer_agent: str = "reviewer",
    reviewer_context: list[str] = None,
    review_criteria: str = "quality, voice consistency, and accuracy",
    channel: str = "api",
) -> str:
    """Run reviewer/gatekeeper review on the latest assistant output."""
    session = get_session(system_key, user_id)

    content_to_review = None
    if session and session.drafts:
        latest = session.latest_draft()
        content_to_review = latest["content"]
        session.stage = "reviewing"
        session.active_agent = reviewer_agent
        session.save()
    else:
        history = get_history(system_key, user_id)
        for msg in reversed(history):
            if msg["role"] == "assistant":
                content_to_review = msg["content"]
                break

    if not content_to_review:
        return "No previous output to review. Create something first!"

    system_prompt = build_system_prompt(
        kb_path=kb_path,
        system_config=system_config or {},
        system_key=system_key,
        agent_key=reviewer_agent,
        extra_context_files=reviewer_context or [],
        shared_config=shared_config,
        session=session,
        channel=channel,
    )

    review_messages = [
        {
            "role": "user",
            "content": (
                f"Please review this output for {review_criteria}:\n\n"
                f"---\n{content_to_review}\n---\n\n"
                f"Provide: (1) Verdict: APPROVED or REVISIONS NEEDED, (2) Specific feedback."
            ),
        }
    ]

    response = await route_to_llm(
        system_prompt=system_prompt,
        messages=review_messages,
        task_type="reasoning",
        system_key=system_key,
    )

    if session:
        session.review = {"verdict": "reviewed", "content": response}
        if "approved" in response.lower():
            session.stage = "approved"
        else:
            session.stage = "iterating"
        session.save()
        response += f"\n\n{session.summary()}"

    return response


async def process_message(
    system_key: str,
    user_id: str,
    message: str,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    channel: str = "api",
    features: dict = None,
    all_systems: dict = None,
    agent_key: str | None = None,
) -> str:
    """
    Main entry point: process an incoming message through the full pipeline.

    Flow:
    0. Detect satisfaction signals from user message (analytics)
    1. Check for active creative session
    2. Check for skill trigger
    3. Select agent and route to LLM
    """
    features = features or {}

    # Step 0: Detect satisfaction signals from user message (non-blocking)
    if _analytics_available:
        result = detect_satisfaction_signal(message)
        if result:
            signal, _confidence = result
            try:
                log_satisfaction(user_id, signal)
            except Exception:
                pass

    # Initialize interaction tracker (non-blocking analytics)
    tracker = None
    if _analytics_available:
        tracker = InteractionTimer(user_id=user_id, system_key=system_key, message=message)
        tracker.__enter__()

    try:
        response = await _process_message_inner(
            system_key=system_key,
            user_id=user_id,
            message=message,
            kb_path=kb_path,
            system_config=system_config,
            shared_config=shared_config,
            channel=channel,
            features=features,
            all_systems=all_systems,
            agent_key=agent_key,
            tracker=tracker,
        )
    except Exception as e:
        if tracker:
            tracker.error = str(e)[:200]
            tracker.__exit__(type(e), e, None)
        raise
    else:
        if tracker:
            tracker.response_length = len(response) if response else 0
            tracker.__exit__(None, None, None)

    return response


async def _process_message_inner(
    system_key: str,
    user_id: str,
    message: str,
    kb_path=None,
    system_config: dict = None,
    shared_config: dict = None,
    channel: str = "api",
    features: dict = None,
    all_systems: dict = None,
    agent_key: str | None = None,
    tracker=None,
) -> str:
    """Inner message processing logic (wrapped by analytics in process_message)."""
    # Step 1: Active session?
    session = get_session(system_key, user_id)
    if session and session.stage not in ("completed", "approved"):
        return await handle_session_message(
            session=session,
            user_id=user_id,
            message=message,
            kb_path=kb_path,
            system_config=system_config,
            shared_config=shared_config,
            channel=channel,
        )

    # Step 2: Skill trigger?
    handled, result = await check_and_execute_skill(
        system_key=system_key,
        user_id=user_id,
        message=message,
        kb_path=kb_path,
        system_config=system_config,
        shared_config=shared_config,
        channel=channel,
    )
    if handled:
        if tracker:
            tracker.skill_name = "skill_triggered"
        return result

    # Step 2.5: Evolution intent? (save to KB, create SOP, update agent, etc.)
    if _evolution_available and has_evolution_intent(message):
        try:
            # Get recent conversation for context
            recent_history = get_history(system_key, user_id)
            conv_context = ""
            if recent_history:
                conv_lines = [f"{m['role']}: {m['content'][:300]}" for m in recent_history[-4:]]
                conv_context = "\n".join(conv_lines)

            evolution_result = await analyze_evolution_intent(
                message=message,
                system_key=system_key,
                conversation_context=conv_context,
            )
            if evolution_result and evolution_result.get("action") != "none":
                # Format a confirmation preview for the user
                action = evolution_result.get("action", "unknown")
                title = evolution_result.get("title", "")
                reason = evolution_result.get("reason", "")
                subfolder = evolution_result.get("subfolder", "")

                preview = (
                    f"**Evolution detected** — I'll {action.replace('_', ' ')}:\n"
                    f"**{title}** → `systems/{system_key}/{subfolder}`\n"
                    f"_{reason}_\n\n"
                    f"Say **proceed** to confirm, or tell me to adjust."
                )
                add_message(system_key, user_id, "user", message)
                add_message(system_key, user_id, "assistant", preview)
                if tracker:
                    tracker.intent = "evolution"
                return preview
        except Exception as e:
            logger.debug(f"Evolution analysis skipped: {e}")

    # Step 3: Agent routing — use config-defined keywords, fall back to agent key names
    agent_routing = {}
    if system_config:
        agent_routing = system_config.get("agent_routing", {})
        if not agent_routing:
            # Fallback: derive keywords from agent key names
            for ak in system_config.get("agents", {}):
                keywords = ak.replace("_", " ").split()
                agent_routing[ak] = keywords

    selected_agent = agent_key or select_agent(agent_routing, message)

    # Log agent and task type to tracker
    task_class = classify_task(message, system_key=system_key)
    if tracker:
        tracker.agent_key = selected_agent
        tracker.task_type = task_class

    return await standard_llm_handling(
        system_key=system_key,
        agent_key=selected_agent,
        user_id=user_id,
        message=message,
        kb_path=kb_path,
        system_config=system_config,
        shared_config=shared_config,
        channel=channel,
        features=features,
        all_systems=all_systems,
    )
