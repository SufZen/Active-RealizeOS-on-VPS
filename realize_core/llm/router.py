"""
Multi-LLM Router: Classifies task type and selects the optimal model.

Reads model routing from realize-os.yaml (llm.routing section) with per-system
overrides (llm.system_overrides). Falls back to hardcoded defaults if config
is unavailable.

Strategy:
- Tier 1 (cheap/free): Simple Q&A, summaries, routing classification
- Tier 2 (mid): Content creation, reasoning, financial analysis, tool use, code
- Tier 3 (premium): Complex strategy, cross-system coordination
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Atomic routing state (replaces separate globals to prevent race conditions)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RoutingState:
    """Immutable routing configuration — atomically swapped on load."""

    config: dict
    overrides: dict
    default_model: str


_routing_state: _RoutingState | None = None

# Map YAML model names → internal model keys used by the registry
_YAML_TO_MODEL_KEY = {
    "gemini-flash": "gemini_flash",
    "gemini-pro": "gemini_pro",
    "gemini-pro-vision": "gemini_pro",
    "claude-sonnet-4-6": "claude_sonnet",
    "claude-opus-4-6": "claude_opus",
    "claude-haiku-4-5": "claude_haiku",
    "veo-2": "gemini_pro",  # No video model in registry, fallback
}

# Map classifier task types → YAML routing keys (when they differ)
_TASK_TYPE_TO_YAML_KEY = {
    # Identity mappings (explicit for completeness)
    "simple": "simple",
    "content": "content",
    "code": "code",
    "complex": "complex",
    # Mappings where task type differs from YAML key
    "reasoning": "strategy",
    "financial": "data",
    "web_research": "web_research",
    "web_action": "web_action",
    "google": "google",
    "image_gen": "image",
    "video_gen": "video",
    "spreadsheet": "data",
}

# All recognized task types (for config validation)
_VALID_TASK_TYPES = set(_TASK_TYPE_TO_YAML_KEY.keys())


def load_routing_config(config: dict = None):
    """Load LLM routing config from realize-os.yaml.

    Called at startup or lazily on first select_model() call.
    Atomically swaps the global _routing_state to prevent race conditions.
    """
    global _routing_state

    if config is None:
        try:
            from realize_core.config import load_config

            config = load_config()
        except Exception as e:
            logger.debug(f"Failed to load config: {e}")
            _routing_state = _RoutingState(config={}, overrides={}, default_model="gemini_flash")
            return

    llm_config = config.get("llm", {})
    routing = llm_config.get("routing", {})
    overrides = llm_config.get("system_overrides", {})
    default_model = llm_config.get("default_model", "gemini-flash")

    # Validate config: warn about unrecognized model names
    known_yaml_models = set(_YAML_TO_MODEL_KEY.keys())
    for key, model_name in routing.items():
        if model_name and model_name not in known_yaml_models:
            # Check if it can be normalized
            normalized = _normalize_model_name(model_name)
            if normalized == model_name.replace("-", "_"):
                logger.warning(f"LLM routing: unrecognized model '{model_name}' for key '{key}'")

    # Atomic swap
    _routing_state = _RoutingState(
        config=routing,
        overrides=overrides,
        default_model=_normalize_model_name(default_model),
    )
    logger.info(
        f"LLM routing loaded: {len(routing)} routes, "
        f"{len(overrides)} system overrides, default={_routing_state.default_model}"
    )


def _normalize_model_name(yaml_model: str) -> str:
    """Convert a YAML model name to an internal model key."""
    if yaml_model in _YAML_TO_MODEL_KEY:
        return _YAML_TO_MODEL_KEY[yaml_model]
    # Fallback: replace dashes with underscores, strip version suffixes
    normalized = yaml_model.replace("-", "_")
    # Try to match common patterns
    if "claude" in normalized and "opus" in normalized:
        return "claude_opus"
    if "claude" in normalized and "sonnet" in normalized:
        return "claude_sonnet"
    if "claude" in normalized and "haiku" in normalized:
        return "claude_haiku"
    if "gemini" in normalized and "flash" in normalized:
        return "gemini_flash"
    if "gemini" in normalized:
        return "gemini_pro"
    return normalized


# ---------------------------------------------------------------------------
# Keyword sets for task classification
# ---------------------------------------------------------------------------

COMPLEX_KEYWORDS = {
    "cross-system",
    "multi-system",
    "strategic analysis",
    "portfolio review",
    "ecosystem",
    "all ventures",
    "all systems",
}

FINANCIAL_KEYWORDS = {
    "deal",
    "roi",
    "irr",
    "investment",
    "financial",
    "budget",
    "capex",
    "revenue",
    "break-even",
    "cash flow",
    "modeling",
    "underwriting",
    "valuation",
    "invoice",
    "payment",
    "accounting",
    "vat",
    "tax",
    "variance",
}

REASONING_KEYWORDS = {
    "analyze",
    "evaluate",
    "compare",
    "assess",
    "contract",
    "legal",
    "compliance",
    "licensing",
    "permit",
    "strategy",
    "architecture",
    "sprint plan",
    "design",
    "sop",
}

CODE_KEYWORDS = {
    "code",
    "function",
    "class",
    "debug",
    "script",
    "program",
    "api",
    "endpoint",
    "refactor",
    "implement",
    "unit test",
    "python",
    "javascript",
    "typescript",
    "sql",
    "fix the bug",
    "pull request",
    "code review",
}

CONTENT_KEYWORDS = {
    "write",
    "blog",
    "post",
    "linkedin",
    "newsletter",
    "article",
    "content",
    "copy",
    "draft",
    "headline",
    "caption",
    "thread",
}

SIMPLE_KEYWORDS = {
    "what is",
    "tell me",
    "explain",
    "summary",
    "summarize",
    "list",
    "show",
    "status",
    "help",
    "how does",
    "define",
    "remind",
    "remember",
    "feedback",
}

GOOGLE_KEYWORDS = {
    "email",
    "emails",
    "gmail",
    "send email",
    "draft email",
    "inbox",
    "mail",
    "unread",
    "send to my email",
    "email me",
    "calendar",
    "schedule",
    "meeting",
    "event",
    "appointment",
    "free time",
    "drive",
    "google drive",
    "google doc",
    "create doc",
    "save to drive",
    "create document",
}

WEB_RESEARCH_KEYWORDS = {
    "search",
    "find online",
    "look up",
    "lookup",
    "research",
    "latest news",
    "check online",
    "find me",
    "browse",
    "website",
    "web page",
    "url",
    "competitor",
    "market data",
    "search the web",
    "find information",
}

WEB_ACTION_KEYWORDS = {
    "post on linkedin",
    "publish online",
    "submit form",
    "fill out",
    "sign up on",
    "register on",
    "book online",
    "log in to",
    "navigate to",
    "go to the site",
    "open the page",
    "fill the form",
    "download from",
}

# All keyword sets mapped to their task type (for score-based classification)
_KEYWORD_SETS: dict[str, set[str]] = {
    "google": GOOGLE_KEYWORDS,
    "web_action": WEB_ACTION_KEYWORDS,
    "web_research": WEB_RESEARCH_KEYWORDS,
    "complex": COMPLEX_KEYWORDS,
    "financial": FINANCIAL_KEYWORDS,
    "reasoning": REASONING_KEYWORDS,
    "code": CODE_KEYWORDS,
    "content": CONTENT_KEYWORDS,
    "simple": SIMPLE_KEYWORDS,
}


def classify_task(message: str, system_key: str = None) -> str:
    """
    Classify a user message into a task type for model selection.

    Uses a two-phase approach:
    1. Priority check for tool-use and complex types (require specific capabilities)
    2. Score-based classification by absolute keyword match count for remaining types

    Args:
        message: The user's message text
        system_key: The target system key (optional, for system-specific defaults)

    Returns:
        Task type string: "simple", "content", "reasoning", "financial",
                          "complex", "code", "google", "web_research", "web_action"
    """
    if not message:
        return "simple"

    msg_lower = message.lower()

    # Phase 1: Priority types — checked first because they require specific capabilities
    # (tool_use for google/web, premium tier for complex)
    priority_checks = [
        ("complex", COMPLEX_KEYWORDS),
        ("google", GOOGLE_KEYWORDS),
        ("web_action", WEB_ACTION_KEYWORDS),
        ("web_research", WEB_RESEARCH_KEYWORDS),
    ]
    for task_type, keywords in priority_checks:
        if any(kw in msg_lower for kw in keywords):
            return task_type

    # Phase 2: Score-based classification by absolute match count.
    # Dict insertion order defines tiebreaker priority (first wins ties).
    scored_sets = {
        "financial": FINANCIAL_KEYWORDS,
        "code": CODE_KEYWORDS,
        "reasoning": REASONING_KEYWORDS,
        "content": CONTENT_KEYWORDS,
        "simple": SIMPLE_KEYWORDS,
    }

    best_type = "simple"
    best_count = 0
    for task_type, keywords in scored_sets.items():
        count = sum(1 for kw in keywords if kw in msg_lower)
        if count > best_count:
            best_count = count
            best_type = task_type

    return best_type


def _get_quality_override(task_type: str) -> str | None:
    """
    Check if quality feedback suggests a model override for this task type.
    Returns a model key if override warranted, None otherwise.

    Self-tuning: if users consistently give negative feedback on a task type,
    the system auto-upgrades to a more capable model.
    """
    try:
        from realize_core.memory.store import get_feedback_signals

        signals = get_feedback_signals(task_type, days=30)
        if not signals:
            return None

        positive = signals.get("positive", 0)
        negative = signals.get("negative", 0) + signals.get("correction", 0)
        resets = signals.get("reset", 0)

        # If many resets/negatives for simple tasks -> upgrade to tier 2
        if task_type == "simple" and (negative + resets * 2) > positive and (negative + resets) >= 3:
            logger.info(f"Self-tuning: upgrading {task_type} from tier1 to tier2 (neg={negative}, resets={resets})")
            return "claude_sonnet"

        # If content tasks have many negatives -> upgrade to tier 3
        if task_type == "content" and resets >= 3 and resets > positive:
            logger.info(f"Self-tuning: upgrading {task_type} from tier2 to tier3")
            return "claude_opus"

    except Exception as e:
        logger.debug(f"Quality override check failed: {e}")

    return None


def select_model(task_type: str, system_key: str = None, conversation_depth: int = 0) -> str:
    """
    Select the LLM model based on task type using realize-os.yaml routing config.

    Priority order:
    1. Self-tuning override (from user feedback signals)
    2. Per-system override (llm.system_overrides in YAML)
    3. YAML routing config (llm.routing in YAML)
    4. Hardcoded fallback map
    5. Config default_model as ultimate fallback

    Args:
        task_type: Classified task type from classify_task()
        system_key: System key for per-system overrides
        conversation_depth: Number of messages in conversation history

    Returns:
        Model identifier string: "gemini_flash", "gemini_pro", "claude_haiku",
        "claude_sonnet", or "claude_opus"
    """
    global _routing_state

    # Lazy-load config if not yet loaded
    if _routing_state is None:
        load_routing_config()

    state = _routing_state  # Local ref for thread safety

    # 1. Self-tuning override from feedback
    override = _get_quality_override(task_type)
    if override:
        return override

    # 2. Per-system override (e.g., arena.complex → claude-opus-4-6)
    if system_key and state.overrides:
        sys_overrides = state.overrides.get(system_key, {})
        yaml_key = _TASK_TYPE_TO_YAML_KEY.get(task_type, task_type)
        yaml_model = sys_overrides.get(yaml_key) or sys_overrides.get(task_type)
        if yaml_model:
            model_key = _normalize_model_name(yaml_model)
            logger.debug(f"System override: {system_key}.{task_type} → {model_key}")
            return model_key

    # 3. YAML routing config
    if state.config:
        yaml_key = _TASK_TYPE_TO_YAML_KEY.get(task_type, task_type)
        yaml_model = state.config.get(yaml_key) or state.config.get(task_type)
        if yaml_model:
            model_key = _normalize_model_name(yaml_model)
            return model_key

    # 4. Hardcoded fallback (backward compatibility)
    fallback_map = {
        "simple": "gemini_flash",
        "content": "claude_sonnet",
        "reasoning": "claude_sonnet",
        "financial": "claude_opus",
        "complex": "claude_opus",
        "code": "claude_sonnet",
        "google": "claude_sonnet",  # Needs tool_use
        "web_research": "claude_sonnet",  # Needs tool_use
        "web_action": "claude_sonnet",  # Needs tool_use
    }

    result = fallback_map.get(task_type)
    if result:
        return result

    # 5. Ultimate fallback: cheapest model for unrecognized types
    return "gemini_flash"


def _log_usage(response) -> None:
    """Log LLM usage for cost tracking (non-blocking)."""
    try:
        from realize_core.memory.store import log_llm_usage

        if response.input_tokens or response.output_tokens:
            log_llm_usage(
                model=response.model or "unknown",
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
            )
    except Exception as e:
        logger.debug(f"Usage logging failed: {e}")


# Task types that should use tool_use (Claude tool calling)
TOOL_TASK_TYPES = {"google", "web_research", "web_action"}

# Maximum tool_use round-trips to prevent infinite loops
MAX_TOOL_ROUNDS = 5


async def _get_tool_schemas(task_type: str) -> list[dict]:
    """Get relevant tool schemas for a task type from the ToolRegistry."""
    try:
        from realize_core.tools.tool_registry import get_tool_registry

        registry = get_tool_registry()
        all_schemas = registry.get_all_schemas(available_only=True)

        if task_type == "google":
            # Google Workspace tools + web tools (for research within Google tasks)
            return [s for s in all_schemas if s["name"].startswith(("gmail_", "calendar_", "drive_", "web_"))]
        elif task_type in ("web_research", "web_action"):
            return [s for s in all_schemas if s["name"].startswith("web_")]
        else:
            return all_schemas
    except Exception as e:
        logger.warning(f"Failed to load tool schemas: {e}")
        return []


async def _execute_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        from realize_core.tools.tool_registry import get_tool_registry

        registry = get_tool_registry()
        result = await registry.execute(tool_name, tool_input)

        if result.success:
            return result.output or "(no output)"
        else:
            return f"Tool error: {result.error}"
    except Exception as e:
        logger.error(f"Tool execution failed for {tool_name}: {e}", exc_info=True)
        return f"Tool execution failed: {str(e)[:300]}"


async def _route_with_tools(
    system_prompt: str,
    messages: list[dict],
    task_type: str,
    model_key: str,
    system_key: str = None,
) -> str:
    """
    Route to LLM with tool_use support. Handles the full loop:
    1. Send message + tool schemas to Claude
    2. If Claude returns tool_use blocks, execute them
    3. Send tool_results back to Claude
    4. Repeat until Claude returns a text response (up to MAX_TOOL_ROUNDS)
    """
    from realize_core.config import MODELS
    from realize_core.llm.claude_client import call_claude_with_tools

    tools = await _get_tool_schemas(task_type)
    if not tools:
        logger.info(f"No tools available for task_type={task_type}, falling back to text-only")
        return None  # Signal caller to fall back to text-only

    # Use the configured model if it's a Claude model, otherwise default to Sonnet
    # (tool_use requires the Anthropic API)
    model = MODELS.get(model_key) if "claude" in model_key else None
    if not model:
        model = MODELS.get("claude_sonnet", "claude-sonnet-4-20250514")
    logger.info(f"Tool-use routing: {len(tools)} tools, model={model}, task={task_type}")

    current_messages = list(messages)

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            response = await call_claude_with_tools(
                system_prompt=system_prompt,
                messages=current_messages,
                tools=tools,
                model=model,
            )
        except RuntimeError as e:
            logger.error(f"Tool-use LLM call failed: {e}")
            return f"I encountered an error while trying to use tools: {e}"

        # Check if Claude wants to use tools
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if hasattr(b, "text") and b.text]

        if not tool_use_blocks:
            # No tool calls — return the text response
            return "\n".join(b.text for b in text_blocks) if text_blocks else ""

        # Execute each tool call
        logger.info(f"Tool-use round {round_num + 1}: {len(tool_use_blocks)} tool(s) requested")

        # Build the assistant message with all content blocks
        assistant_content = []
        for block in response.content:
            if block.type == "tool_use":
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
            elif hasattr(block, "text"):
                assistant_content.append(
                    {
                        "type": "text",
                        "text": block.text,
                    }
                )

        current_messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools and build tool_result messages
        tool_results = []
        for block in tool_use_blocks:
            logger.info(f"  Executing tool: {block.name}({list(block.input.keys())})")
            result_text = await _execute_tool_call(block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text[:4000],  # Truncate to prevent context overflow
                }
            )

        current_messages.append({"role": "user", "content": tool_results})

    # If we exhausted rounds, return whatever we have
    logger.warning(f"Tool-use loop exhausted after {MAX_TOOL_ROUNDS} rounds")
    return "I completed several tool operations but ran out of processing rounds. Please ask again if you need more."


async def route_to_llm(
    system_prompt: str,
    messages: list[dict],
    task_type: str,
    system_key: str = None,
    conversation_depth: int = 0,
) -> str:
    """
    Route the request to the appropriate LLM based on task type.

    For tool-capable task types (google, web_research, web_action), uses
    Claude's tool_use API with an execution loop. For all other types,
    uses standard text completion.

    Args:
        system_prompt: Assembled system prompt
        messages: Conversation history
        task_type: Classified task type from classify_task()
        system_key: System key for per-system model overrides (optional)
        conversation_depth: Number of messages in conversation history

    Returns:
        LLM response text
    """
    model_key = select_model(task_type, system_key=system_key, conversation_depth=conversation_depth)
    logger.info(f"Routing to {model_key} for task_type={task_type} system={system_key}")

    # Tool-use path: handle Google, web search, web action with Claude tool calling
    if task_type in TOOL_TASK_TYPES:
        tool_result = await _route_with_tools(
            system_prompt=system_prompt,
            messages=messages,
            task_type=task_type,
            model_key=model_key,
            system_key=system_key,
        )
        if tool_result is not None:
            return tool_result
        # Fall through to text-only if tools unavailable

    # Try registry-based routing first
    try:
        from realize_core.llm.registry import get_registry

        registry = get_registry()
        provider = registry.get_provider(model_key)

        if provider and provider.is_available():
            model_id = registry.resolve_model_id(model_key)
            response = await provider.complete(
                system_prompt=system_prompt,
                messages=messages,
                model=model_id,
            )
            if response.ok:
                registry.record_success(provider.name)
                _log_usage(response)
                return response.text
            # If provider returned an error, record failure and try fallback
            registry.record_failure(provider.name)
            logger.warning(f"Provider {provider.name} error: {response.error}, trying fallback")
            fallback = registry.get_fallback(model_key)
            if fallback:
                fb_response = await fallback.complete(
                    system_prompt=system_prompt,
                    messages=messages,
                )
                if fb_response.ok:
                    registry.record_success(fallback.name)
                    _log_usage(fb_response)
                    return fb_response.text
                registry.record_failure(fallback.name)

            # Return the error text as last resort
            return response.text

        elif provider:
            # Provider registered but not available — try fallback
            logger.warning(f"Provider for {model_key} not available, trying fallback")
            fallback = registry.get_fallback(model_key)
            if fallback:
                response = await fallback.complete(system_prompt=system_prompt, messages=messages)
                if response.ok:
                    registry.record_success(fallback.name)
                _log_usage(response)
                return response.text

    except Exception as e:
        logger.warning(f"Registry routing failed, falling back to direct calls: {e}")

    # Emergency fallback: direct client import (backward compatibility)
    logger.warning(f"Using emergency legacy fallback for model_key={model_key}")
    from realize_core.llm.claude_client import call_claude_opus, call_claude_sonnet
    from realize_core.llm.gemini_client import call_gemini_flash, call_gemini_pro

    if model_key == "gemini_flash":
        return await call_gemini_flash(system_prompt, messages)
    elif model_key == "gemini_pro":
        return await call_gemini_pro(system_prompt, messages)
    elif model_key == "claude_sonnet":
        return await call_claude_sonnet(system_prompt, messages)
    elif model_key == "claude_opus":
        return await call_claude_opus(system_prompt, messages)
    else:
        return await call_gemini_flash(system_prompt, messages)
