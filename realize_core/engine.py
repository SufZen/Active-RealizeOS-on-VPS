"""
Canonical runtime entrypoint for channel adapters.

Loads the current project configuration, resolves the target system, and
delegates execution to the shared base_handler pipeline.
"""

import logging
from pathlib import Path

from realize_core.base_handler import process_message as handle_message

logger = logging.getLogger(__name__)

_memory_initialized = False


def _default_shared_config() -> dict:
    return {
        "identity": "shared/identity.md",
        "preferences": "shared/user-preferences.md",
    }


def _resolve_kb_path(config: dict) -> Path:
    from realize_core.config import KB_PATH

    return Path(config.get("kb_path", KB_PATH)).resolve()


def route_to_system(text: str, systems: dict, default: str = "personal") -> str:
    """
    Smart system router: score a message against all systems' agent_routing
    keywords and return the best-matching system_key.

    Uses word-boundary matching to avoid false substring hits ("do" matching
    "windows"). System names and keys get automatic high-weight scoring.

    Used by super_agent mode Telegram bots when no explicit system is set.
    Falls back to `default` if no keywords match.
    """
    import re

    scores: dict[str, float] = {}
    text_lower = text.lower()
    # Tokenize for word-boundary matching
    words = set(re.findall(r"[a-zA-Z\u00C0-\u024F]+", text_lower))

    # Common words that should not influence routing (too generic)
    STOP_WORDS = {
        "help", "hi", "hello", "hey", "question", "how", "what", "can",
        "please", "need", "want", "do", "should", "is", "the", "a", "an",
        "this", "that", "it", "my", "me", "i", "we", "you", "your",
        "but", "and", "or", "to", "for", "in", "on", "of", "with",
        "about", "tell", "topic", "venture", "bit", "plan",
    }

    for sys_key, sys_conf in systems.items():
        score = 0.0

        # Phase 1: System identity matching (high weight)
        # Match system key itself (e.g. "burtucala", "arena", "realizeos")
        sys_key_clean = sys_key.replace("-", " ").replace("_", " ").lower()
        sys_name = sys_conf.get("name", "").lower()
        for identity_word in set(sys_key_clean.split() + sys_name.split()):
            if len(identity_word) >= 3 and identity_word in words:
                score += 5.0  # High weight for system name match

        # Phase 2: Agent routing keywords (word-boundary, skip stop words)
        agent_routing = sys_conf.get("agent_routing", {})
        matched_keywords = set()
        for _agent, keywords in agent_routing.items():
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in STOP_WORDS:
                    continue
                if kw_lower in matched_keywords:
                    continue
                # Multi-word keywords: check substring
                if " " in kw_lower or "-" in kw_lower:
                    if kw_lower in text_lower:
                        score += 1.5
                        matched_keywords.add(kw_lower)
                # Single-word: require word boundary match
                elif kw_lower in words:
                    score += 1.0
                    matched_keywords.add(kw_lower)

        if score > 0:
            scores[sys_key] = score

    if not scores:
        return default if default in systems else next(iter(systems))

    best = max(scores, key=scores.get)
    logger.info(f"Smart router: '{text[:60]}...' → {best} (score={scores[best]:.1f}, candidates={{{', '.join(f'{k}: {v:.1f}' for k, v in sorted(scores.items(), key=lambda x: -x[1]))}}})")
    return best


def _resolve_system(
    systems: dict,
    requested_system_key: str,
) -> tuple[str, dict]:
    if requested_system_key:
        if requested_system_key in systems:
            return requested_system_key, systems[requested_system_key]
        available = ", ".join(sorted(systems))
        raise KeyError(f"System '{requested_system_key}' not found. Available systems: {available}")

    if len(systems) == 1:
        key, config = next(iter(systems.items()))
        return key, config

    # Multi-system with no explicit key: use smart routing
    # (This path is reached when a super_agent bot sends a message without
    #  a system_key — the route_to_system function was already called by
    #  the channel adapter, so this is a fallback that shouldn't normally trigger)
    available = ", ".join(sorted(systems))
    raise KeyError(f"No system selected. Choose one of: {available}")


def _ensure_memory_store():
    global _memory_initialized
    if _memory_initialized:
        return

    from realize_core.memory.store import init_db

    init_db()
    _memory_initialized = True


async def process_message(
    user_id: str,
    text: str,
    system_key: str = "",
    channel: str = "api",
    topic_id: str = "",
    image_data: bytes = b"",
    image_media_type: str = "",
    agent_key: str | None = None,
    file_data: bytes = b"",
    file_name: str = "",
) -> str:
    """
    Resolve runtime context for channel adapters and delegate to base_handler.

    Extra transport-specific payloads are accepted for forward compatibility.
    The current core handler only consumes the text path.
    """
    del topic_id, image_data, image_media_type, file_data, file_name

    from realize_core.config import build_systems_dict, get_features, load_config

    _ensure_memory_store()

    config = load_config()
    kb_path = _resolve_kb_path(config)
    systems = build_systems_dict(config, kb_path=kb_path)
    if not systems:
        return "No systems are configured. Add at least one system to realize-os.yaml first."

    shared_config = config.get("shared", _default_shared_config())
    features = get_features(config)

    try:
        resolved_system_key, system_config = _resolve_system(systems, system_key)
    except KeyError as exc:
        logger.warning("Channel request could not resolve system: %s", exc)
        return str(exc)

    return await handle_message(
        system_key=resolved_system_key,
        user_id=user_id,
        message=text,
        kb_path=kb_path,
        system_config=system_config,
        shared_config=shared_config,
        channel=channel,
        features=features,
        all_systems=systems,
        agent_key=agent_key,
    )
