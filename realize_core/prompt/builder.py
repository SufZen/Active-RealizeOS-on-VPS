"""
Prompt Builder: Reads KB markdown files and assembles multi-layer system prompts.

Layers (assembled in optimized order for LLM primacy/recency attention):
1. Identity layer (shared/identity.md + preferences)
2. Agent layer (selected agent definition .md file)
3. Venture layer (F-foundations/venture-identity.md + venture-voice.md)
4. Session layer (active creative session state)
5. Dynamic KB context (RAG: semantic search results)
6. Extra context files (user-loaded)
7. Memory layer (I-insights/learning-log.md)
8. Cross-system context (when cross_system feature enabled, capped at 2500 chars)
9. Routing context (A-agents/_README.md — orchestrator only)
10. Proactive behavior instructions (when proactive_mode enabled)
11. Channel format instructions
"""

import logging
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Layer configuration: budget, priority, compressibility
# ---------------------------------------------------------------------------

# Priority levels for smart truncation (lower number = higher priority = last to compress)
_PRIORITY_HIGH = 1
_PRIORITY_MEDIUM = 2
_PRIORITY_LOW = 3

LAYER_CONFIG = {
    "identity": {"max_chars": 2000, "priority": _PRIORITY_HIGH, "compressible": False},
    "agent": {"max_chars": 3000, "priority": _PRIORITY_HIGH, "compressible": False},
    "venture": {"max_chars": 2500, "priority": _PRIORITY_HIGH, "compressible": False},
    "venture_voice": {"max_chars": 1500, "priority": _PRIORITY_MEDIUM, "compressible": True, "compressed_max": 800},
    "session": {"max_chars": 2000, "priority": _PRIORITY_HIGH, "compressible": False},
    "kb_index": {"max_chars": 1200, "priority": _PRIORITY_MEDIUM, "compressible": True, "compressed_max": 600},
    "extra": {"max_chars": 2000, "priority": _PRIORITY_MEDIUM, "compressible": True, "compressed_max": 1000},
    "memory": {"max_chars": 1500, "priority": _PRIORITY_LOW, "compressible": True, "compressed_max": 750},
    "cross_system": {"max_chars": 2500, "priority": _PRIORITY_LOW, "compressible": True, "compressed_max": 1200},
    "routing": {"max_chars": 2000, "priority": _PRIORITY_LOW, "compressible": True, "compressed_max": 1000},
    "proactive": {"max_chars": 800, "priority": _PRIORITY_LOW, "compressible": True, "compressed_max": 400},
    "channel": {"max_chars": 600, "priority": _PRIORITY_HIGH, "compressible": False},
}

# Default total budget (~5000 tokens)
_DEFAULT_MAX_TOTAL_CHARS = 20000

# ---------------------------------------------------------------------------
# File cache with LRU eviction
# ---------------------------------------------------------------------------

_MAX_CACHE_SIZE = 200
_file_cache: OrderedDict[str, str] = OrderedDict()
_file_mtimes: dict[str, float] = {}  # normalized_path → last known mtime

# ---------------------------------------------------------------------------
# Semantic search import (lazy, module-level)
# ---------------------------------------------------------------------------

_semantic_search = None
_semantic_search_checked = False
_list_resources = None
_list_resources_checked = False


def _get_semantic_search():
    """Lazy-load semantic_search function once."""
    global _semantic_search, _semantic_search_checked
    if _semantic_search_checked:
        return _semantic_search
    _semantic_search_checked = True
    try:
        from realize_core.kb.indexer import semantic_search

        _semantic_search = semantic_search
    except ImportError:
        logger.debug("KB indexer not available — RAG disabled")
    except Exception as e:
        logger.debug(f"KB indexer failed to load: {e}")
    return _semantic_search


def _get_list_resources():
    """Lazy-load list_resources function once."""
    global _list_resources, _list_resources_checked
    if _list_resources_checked:
        return _list_resources
    _list_resources_checked = True
    try:
        from realize_core.kb.indexer import list_resources

        _list_resources = list_resources
    except ImportError:
        logger.debug("KB indexer not available — kb_index layer disabled")
    except Exception as e:
        logger.debug(f"KB indexer failed to load: {e}")
    return _list_resources


# ---------------------------------------------------------------------------
# Channel format instructions
# ---------------------------------------------------------------------------

CHANNEL_FORMAT_INSTRUCTIONS = {
    "telegram": (
        "## Writing Style\n"
        "You are responding inside Telegram. Write like a sharp, thoughtful person "
        "texting a smart colleague -- not like a formatted report.\n\n"
        "How to write:\n"
        "- Lead with the answer, not context or preamble\n"
        "- Write in flowing sentences and short paragraphs (2-3 sentences)\n"
        "- Use bold sparingly -- only for critical terms\n"
        "- Use bullet points only when listing 4+ distinct items\n"
        "- No section headers, no horizontal rules, no numbered lists for prose\n"
        "- No emoji headers or decorative emoji\n"
        "- No markdown headers (# ## ###)\n\n"
        "What NOT to do:\n"
        "- No opening ceremonies ('Here is my analysis...', 'Great question...')\n"
        "- No closing ceremonies ('In summary...', 'Let me know if...')\n"
        "- No meta-commentary about your own response\n\n"
        "Length: Under 300 words for most responses."
    ),
    "api": (
        "## Response Format\n"
        "Format your response as clean, readable text. "
        "You may use markdown for structure (headers, lists, bold, italic). "
        "Keep responses focused and well-organized. "
        "Lead with the answer, not preamble."
    ),
    "slack": (
        "## Response Format\n"
        "You are responding in Slack. Use Slack mrkdwn formatting. "
        "Keep messages concise and scannable. Use threads for long responses."
    ),
}


# ---------------------------------------------------------------------------
# Token estimation & budget enforcement
# ---------------------------------------------------------------------------


def _estimate_tokens(char_count: int) -> int:
    """Estimate token count from character count. ~4 chars per token for English."""
    return char_count // 4


def _compress_layers(layers: list[tuple[str, str, str]], max_total_chars: int) -> list[tuple[str, str, str]]:
    """
    Compress layers to fit within max_total_chars budget.

    Args:
        layers: List of (layer_name, content, layer_key) tuples.
        max_total_chars: Maximum total characters allowed.

    Returns:
        Compressed layers list (same format, content may be truncated).
    """
    total = sum(len(content) for _, content, _ in layers)
    if total <= max_total_chars:
        return layers

    excess = total - max_total_chars

    # Sort compressible layers by priority (LOW first, then MEDIUM)
    compressible = [
        (i, name, content, key)
        for i, (name, content, key) in enumerate(layers)
        if LAYER_CONFIG.get(key, {}).get("compressible", False)
    ]
    compressible.sort(key=lambda x: -LAYER_CONFIG.get(x[3], {}).get("priority", _PRIORITY_MEDIUM))

    result = list(layers)
    for idx, name, content, key in compressible:
        if excess <= 0:
            break
        config = LAYER_CONFIG.get(key, {})
        compressed_max = config.get("compressed_max", len(content) // 2)
        if len(content) > compressed_max:
            savings = len(content) - compressed_max
            truncated = content[:compressed_max] + f"\n\n[...compressed to {compressed_max} chars]"
            result[idx] = (name, truncated, key)
            excess -= savings

    if excess > 0:
        logger.warning(
            f"Prompt exceeds budget by {excess} chars after compression "
            f"(total ~{total} chars, budget {max_total_chars})"
        )

    return result


# ---------------------------------------------------------------------------
# File I/O with caching
# ---------------------------------------------------------------------------


def _normalize_cache_key(relative_path: str) -> str:
    """Normalize path separators for consistent cache keys across platforms."""
    return relative_path.replace("\\", "/")


def _read_kb_file(kb_path: Path, relative_path: str, max_chars: int = 6000) -> str:
    """
    Read a file from the knowledge base, with LRU caching, mtime checking, and truncation.

    Cache auto-invalidates when file mtime changes (no restart needed for KB updates).
    Cache is bounded to _MAX_CACHE_SIZE entries with LRU eviction.

    Args:
        kb_path: Root path of the KB
        relative_path: Path relative to kb_path
        max_chars: Maximum characters to include

    Returns:
        File content string, or empty string if file not found.
    """
    cache_key = _normalize_cache_key(relative_path)
    file_path = kb_path / cache_key

    # Check if cached version is still valid
    if cache_key in _file_cache:
        try:
            current_mtime = file_path.stat().st_mtime
            if current_mtime <= _file_mtimes.get(cache_key, 0):
                # Move to end (most recently used)
                _file_cache.move_to_end(cache_key)
                content = _file_cache[cache_key]
                if len(content) > max_chars:
                    content = content[:max_chars] + f"\n\n[...truncated at {max_chars} chars]"
                return content
            # File changed — invalidate cache entry
            del _file_cache[cache_key]
            _file_mtimes.pop(cache_key, None)
        except FileNotFoundError:
            _file_cache.pop(cache_key, None)
            _file_mtimes.pop(cache_key, None)
            return ""
        except Exception as e:
            logger.debug(f"Cache check failed for {file_path}: {e}")

    # Read fresh — get mtime first to avoid race
    try:
        file_stat = file_path.stat()
        content = file_path.read_text(encoding="utf-8-sig")

        # LRU eviction: remove oldest entries if cache is full
        while len(_file_cache) >= _MAX_CACHE_SIZE:
            evicted_key, _ = _file_cache.popitem(last=False)
            _file_mtimes.pop(evicted_key, None)

        _file_cache[cache_key] = content
        _file_mtimes[cache_key] = file_stat.st_mtime
    except FileNotFoundError:
        logger.debug(f"KB file not found: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return ""

    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n[...truncated at {max_chars} chars]"

    return content


def clear_cache():
    """Clear the file cache (call after KB update)."""
    _file_cache.clear()
    _file_mtimes.clear()


def get_cache_size() -> int:
    """Return the current number of cached files."""
    return len(_file_cache)


def warm_cache(kb_path: Path, systems: dict, shared_config: dict = None):
    """Pre-read all system KB files into cache at startup."""
    count = 0

    # Warm shared paths
    if shared_config:
        for key in ["identity", "preferences"]:
            path = shared_config.get(key)
            if path and _read_kb_file(kb_path, path):
                count += 1

    # Warm per-system paths
    for system_key, system_config in systems.items():
        for path_key in ["brand_identity", "brand_voice", "state_map", "agents_readme"]:
            path = system_config.get(path_key)
            if path and _read_kb_file(kb_path, path):
                count += 1
        for agent_key, agent_path in system_config.get("agents", {}).items():
            if agent_path and _read_kb_file(kb_path, agent_path):
                count += 1

    logger.info(f"Prompt cache warmed: {count} files pre-loaded")


# ---------------------------------------------------------------------------
# Layer builders
# ---------------------------------------------------------------------------


def _build_identity_layer(kb_path: Path, shared_config: dict) -> str:
    """Build the shared identity layer."""
    identity_path = shared_config.get("identity", "shared/identity.md")
    prefs_path = shared_config.get("preferences", "shared/user-preferences.md")

    id_max = LAYER_CONFIG["identity"]["max_chars"]
    identity = _read_kb_file(kb_path, identity_path, max_chars=id_max)
    preferences = _read_kb_file(kb_path, prefs_path, max_chars=1000)

    if not identity:
        logger.warning(f"Identity file not found: {identity_path}")

    parts = []
    if identity:
        parts.append(f"## Identity\n{identity}")
    if preferences:
        parts.append(f"## User Preferences\n{preferences}")

    return "\n\n".join(parts)


def _build_brand_layer(kb_path: Path, system_config: dict) -> str:
    """Build the venture layer for a specific system."""
    parts = []

    brand_identity_path = system_config.get("brand_identity")
    if brand_identity_path:
        content = _read_kb_file(kb_path, brand_identity_path, max_chars=LAYER_CONFIG["venture"]["max_chars"])
        if content:
            parts.append(f"## Venture Identity — {system_config.get('name', 'System')}\n{content}")
        else:
            logger.warning(f"Venture identity file not found: {brand_identity_path}")

    brand_voice_path = system_config.get("brand_voice")
    if brand_voice_path:
        content = _read_kb_file(kb_path, brand_voice_path, max_chars=LAYER_CONFIG["venture_voice"]["max_chars"])
        if content:
            parts.append(f"## Venture Voice\n{content}")

    return "\n\n".join(parts)


def _build_agent_layer(kb_path: Path, system_config: dict, agent_key: str) -> str:
    """Load a specific agent definition."""
    agent_path = system_config.get("agents", {}).get(agent_key)
    if not agent_path:
        logger.warning(f"Agent {agent_key} not found in system config")
        return ""

    content = _read_kb_file(kb_path, agent_path, max_chars=LAYER_CONFIG["agent"]["max_chars"])
    if content:
        return f"## Active Agent: {agent_key}\n{content}"
    return ""


def _build_routing_context(kb_path: Path, system_config: dict) -> str:
    """Load the agents readme (routing table) for orchestrator awareness."""
    agents_readme = system_config.get("agents_readme")
    if not agents_readme:
        return ""
    readme = _read_kb_file(kb_path, agents_readme, max_chars=LAYER_CONFIG["routing"]["max_chars"])
    if readme:
        return f"## Team Routing Guide\n{readme}"
    return ""


def _build_memory_layer(kb_path: Path, system_config: dict) -> str:
    """Load recent memory (learning log) for context."""
    memory_dir = system_config.get("memory_dir", system_config.get("insights_dir", ""))
    if not memory_dir:
        return ""

    mem_max = LAYER_CONFIG["memory"]["max_chars"]
    per_file_max = mem_max // 2
    learning_log = _read_kb_file(kb_path, f"{memory_dir}/learning-log.md", max_chars=per_file_max)

    parts = []
    if learning_log:
        parts.append(f"## Recent Learning\n{learning_log}")

    # Load Paulo's persistent memory (from /remember command)
    paulo_memory = _read_kb_file(kb_path, f"{memory_dir}/paulo-memory.md", max_chars=per_file_max)
    if paulo_memory:
        parts.append(f"## Paulo's Memory\n{paulo_memory}")

    return "\n\n".join(parts)


def _build_dynamic_kb_context(
    kb_path: Path,
    system_key: str,
    user_message: str,
    extra_context_files: list[str] | None = None,
) -> str:
    """
    Build a compact KB table of contents for the active system.

    Emits one line per resource (path — summary), ordered by FABRIC layer.
    Agents use kb_get(path) or kb_search(query) to fetch full content on demand.
    Falls back to a minimal semantic-search result list if the manifest is empty.
    """
    list_fn = _get_list_resources()

    if list_fn is not None:
        try:
            resources = list_fn(system_key=system_key)
            if resources:
                loaded_paths = set(extra_context_files or [])
                lines = []
                for r in resources:
                    if r["path"] in loaded_paths:
                        continue
                    summary = r.get("summary") or ""
                    layer = r.get("layer", "")
                    lines.append(f"`{r['path']}` [{layer}] — {summary}")

                if lines:
                    header = (
                        "## Knowledge Base Index\n"
                        "_Use `kb_get(path)` to read a file, `kb_search(query)` for semantic search._\n\n"
                    )
                    return header + "\n".join(lines)
        except Exception as e:
            logger.debug(f"KB manifest ToC failed, falling back to semantic search: {e}")

    # Fallback: semantic search result paths (no full content)
    if not user_message or len(user_message) < 10:
        return ""

    search_fn = _get_semantic_search()
    if search_fn is None:
        return ""

    try:
        results = search_fn(user_message, system_key=system_key, top_k=5)
        if not results:
            return ""

        loaded_paths = set(extra_context_files or [])
        lines = []
        for r in results:
            if r["path"] not in loaded_paths:
                snippet = r.get("snippet", "")[:120]
                lines.append(f"`{r['path']}` — {snippet}")

        if lines:
            header = (
                "## Relevant KB Files\n"
                "_Use `kb_get(path)` to read full content._\n\n"
            )
            return header + "\n".join(lines)
    except Exception as e:
        logger.debug(f"Dynamic KB context skipped: {e}")

    return ""


def _build_session_layer(session) -> str:
    """Build session context for the system prompt."""
    if not session:
        return ""

    parts = ["## Active Creative Session"]
    parts.append(f"**Task:** {session.task_type} | **Stage:** {session.stage}")
    parts.append(f"**Brief:** {session.brief}")

    if session.pipeline:
        pipeline_display = []
        for i, agent in enumerate(session.pipeline):
            if i < session.pipeline_index:
                pipeline_display.append(f"[done] {agent}")
            elif i == session.pipeline_index:
                pipeline_display.append(f"[ACTIVE] {agent}")
            else:
                pipeline_display.append(f"[next] {agent}")
        parts.append(f"**Pipeline:** {' -> '.join(pipeline_display)}")

    if hasattr(session, "drafts") and session.drafts:
        parts.append(f"**Drafts:** {len(session.drafts)} version(s)")
        if hasattr(session, "latest_draft"):
            latest = session.latest_draft()
            if latest:
                draft_preview = latest["content"][:2000]
                parts.append(f"**Latest draft (v{latest['version']}, by {latest['agent']}):**\n{draft_preview}")

    if hasattr(session, "review") and session.review:
        parts.append(f"**Last Review:** {session.review.get('verdict', 'pending')}")

    if hasattr(session, "context_files") and session.context_files:
        parts.append(f"**User-loaded context files:** {', '.join(session.context_files)}")

    return "\n".join(parts)


def _build_proactive_instructions(agent_key: str, session=None) -> str:
    """Build compact proactive collaboration instructions."""
    parts = [
        "## Collaboration Instructions\n"
        "You are part of an AI operations team. Be proactive and collaborative:\n"
        "- If a request is vague, ASK clarifying questions before starting\n"
        "- After completing work, SUGGEST logical next steps\n"
        "- If another agent's input would help, SAY SO\n"
        "- Incorporate feedback and explain changes"
    ]

    if session:
        stage_instructions = {
            "briefing": (
                "\n**Current stage: BRIEFING** — Confirm you understand the request. "
                "Ask clarifying questions (audience, tone, format). "
                "Only start drafting once the brief is clear."
            ),
            "drafting": (
                "\n**Current stage: DRAFTING** — Create your best work. "
                "After delivering, offer options: review, iterate, or advance."
            ),
            "iterating": ("\n**Current stage: ITERATING** — Incorporate feedback, explain changes."),
            "reviewing": (
                "\n**Current stage: REVIEWING** — Review thoroughly: voice, accuracy, structure. "
                "Give a clear verdict: APPROVED or REVISIONS NEEDED."
            ),
        }
        if session.stage in stage_instructions:
            parts.append(stage_instructions[session.stage])

    parts.append(
        "\n**Push-Back Protocol:** Challenge decisions when your analysis contradicts the user's direction. "
        "Say 'I don't know' rather than guessing. Flag conflicts with stated preferences. "
        "Honest pushback is a core responsibility."
    )

    # Agent-specific proactive behavior
    if agent_key in ("writer", "content_creator", "copywriter"):
        parts.append(
            "\nAs a content agent, always clarify: target audience, channel/format, "
            "tone register, and any specific references to include."
        )
    elif agent_key in ("analyst", "deal_analyst", "strategist"):
        parts.append(
            "\nAs an analyst, always ask for: key constraints, data sources, "
            "success criteria, and timeline before analyzing."
        )

    return "\n".join(parts)


def _build_cross_system_context(
    kb_path: Path,
    system_key: str,
    all_systems: dict,
    max_total_chars: int = 2500,
) -> str:
    """
    Build cross-system awareness context, capped at max_total_chars total.
    Distributes budget proportionally across other systems.
    """
    if not all_systems or len(all_systems) <= 1:
        return ""

    other_keys = [k for k in all_systems if k != system_key]
    if not other_keys:
        return ""

    # Budget per system (reserve ~200 chars for header and section markers)
    per_system_budget = max(200, (max_total_chars - 100) // len(other_keys))

    parts = ["## Cross-System Awareness\nYou have context across all ventures in this portfolio:"]

    for other_key in other_keys:
        other_config = all_systems[other_key]
        other_name = other_config.get("name", other_key)
        section = [f"\n### {other_name} ({other_key})"]
        section_chars = len(section[0])

        # Read state map for current status
        state_budget = min(per_system_budget * 2 // 3, per_system_budget - 100)
        state_map_path = other_config.get("state_map", "")
        if state_map_path:
            state = _read_kb_file(kb_path, state_map_path, max_chars=state_budget)
            if state:
                section.append(f"**Current State:**\n{state}")
                section_chars += len(state) + 20

        # Read venture identity summary with remaining budget
        brand_budget = max(100, per_system_budget - section_chars)
        brand_path = other_config.get("brand_identity", "")
        if brand_path:
            brand = _read_kb_file(kb_path, brand_path, max_chars=brand_budget)
            if brand:
                section.append(f"**Venture Summary:**\n{brand}")

        if len(section) > 1:
            parts.append("\n".join(section))

    if len(parts) <= 1:
        return ""

    result = "\n\n".join(parts)

    # Hard cap on total cross-system context
    if len(result) > max_total_chars:
        result = result[:max_total_chars] + "\n\n[...cross-system context truncated]"

    return result


# ---------------------------------------------------------------------------
# Main assembly
# ---------------------------------------------------------------------------


def build_system_prompt(
    kb_path: Path,
    system_config: dict,
    system_key: str,
    agent_key: str = "orchestrator",
    user_message: str = "",
    session=None,
    extra_context_files: list[str] | None = None,
    shared_config: dict = None,
    channel: str = "api",
    features: dict = None,
    all_systems: dict = None,
    max_total_chars: int = _DEFAULT_MAX_TOTAL_CHARS,
) -> str:
    """
    Assemble the full system prompt from KB layers.

    Layer order optimized for LLM primacy/recency attention pattern:
    high-importance layers at the beginning and end of the prompt.

    Args:
        kb_path: Root path of the knowledge base
        system_config: System configuration dict (from build_systems_dict)
        system_key: System identifier
        agent_key: Which agent to activate
        user_message: Current user message (for RAG context injection)
        session: Active creative session (if any)
        extra_context_files: Additional KB files to load
        shared_config: Shared configuration (identity, preferences paths)
        channel: Channel name for format instructions
        features: Feature flags dict (from get_features())
        all_systems: All system configs (for cross-system context)
        max_total_chars: Maximum total prompt size in characters (default 20000)

    Returns:
        Assembled system prompt string.
    """
    shared_config = shared_config or {"identity": "shared/identity.md", "preferences": "shared/user-preferences.md"}
    features = features or {}
    # layers: list of (layer_name, content, layer_key) for budget management
    layers: list[tuple[str, str, str]] = []

    # Layer 1: Identity (HIGH priority — who you are)
    identity = _build_identity_layer(kb_path, shared_config)
    if identity:
        layers.append(("identity", identity, "identity"))

    # Layer 2: Agent definition (HIGH priority — what you do, moved up for primacy)
    agent = _build_agent_layer(kb_path, system_config, agent_key)
    if agent:
        layers.append(("agent", agent, "agent"))

    # Layer 3: Venture identity & voice (HIGH priority — brand context)
    brand = _build_brand_layer(kb_path, system_config)
    if brand:
        layers.append(("venture", brand, "venture"))

    # Layer 4: Session (HIGH priority — current task state, moved up)
    session_ctx = _build_session_layer(session)
    if session_ctx:
        layers.append(("session", session_ctx, "session"))

    # Layer 5: KB index ToC (MEDIUM priority — compact compass, agents navigate on demand)
    dynamic_kb = _build_dynamic_kb_context(kb_path, system_key, user_message, extra_context_files)
    if dynamic_kb:
        layers.append(("kb_index", dynamic_kb, "kb_index"))

    # Layer 6: Extra context files (user-loaded — MEDIUM priority)
    if extra_context_files:
        extra_parts = []
        for ctx_file in extra_context_files:
            content = _read_kb_file(kb_path, ctx_file, max_chars=LAYER_CONFIG["extra"]["max_chars"])
            if content:
                extra_parts.append(f"## Loaded Context: {ctx_file}\n{content}")
        if extra_parts:
            layers.append(("extra", "\n\n".join(extra_parts), "extra"))

    # Layer 7: Memory (LOW priority)
    memory = _build_memory_layer(kb_path, system_config)
    if memory:
        layers.append(("memory", memory, "memory"))

    # Layer 8: Cross-system context (LOW priority, capped at 2500 chars)
    if features.get("cross_system") and all_systems:
        cross_system = _build_cross_system_context(
            kb_path,
            system_key,
            all_systems,
            max_total_chars=LAYER_CONFIG["cross_system"]["max_chars"],
        )
        if cross_system:
            layers.append(("cross_system", cross_system, "cross_system"))

    # Layer 9: Routing context (LOW priority — orchestrator only)
    if agent_key == "orchestrator":
        routing = _build_routing_context(kb_path, system_config)
        if routing:
            layers.append(("routing", routing, "routing"))

    # Layer 10: Proactive instructions (LOW priority, conditional on feature flag)
    if features.get("proactive_mode", True):
        proactive = _build_proactive_instructions(agent_key, session)
        if proactive:
            layers.append(("proactive", proactive, "proactive"))

    # Layer 11: Channel format instructions (HIGH priority — at end for recency)
    format_instructions = CHANNEL_FORMAT_INSTRUCTIONS.get(channel, CHANNEL_FORMAT_INSTRUCTIONS["api"])
    layers.append(("channel", format_instructions, "channel"))

    # Budget enforcement: compress layers if total exceeds budget
    layers = _compress_layers(layers, max_total_chars)

    # Log prompt metrics
    total_chars = sum(len(content) for _, content, _ in layers)
    total_tokens = _estimate_tokens(total_chars)
    layer_summary = ", ".join(f"{name}={len(content)}" for name, content, _ in layers)
    logger.debug(f"Prompt assembled: {total_chars} chars (~{total_tokens} tokens), layers: [{layer_summary}]")

    if total_chars > max_total_chars * 0.8:
        logger.warning(
            f"Prompt size {total_chars} chars (~{total_tokens} tokens) approaching budget of {max_total_chars} chars"
        )

    return "\n\n---\n\n".join(content for _, content, _ in layers)
