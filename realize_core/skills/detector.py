"""
Skills System: Auto-triggered contextual workflows.

Skills can be defined as:
1. YAML v1 (trigger -> pipeline) — simple agent sequence
2. YAML v2 (trigger -> multi-step workflow with tools, conditions, human-in-the-loop)
3. Hardcoded fallback in _DEFAULT_SKILLS (reliability when YAML missing)

The system auto-detects schema version: if a skill has a 'steps' key, it's v2.
Use reload_skills() to pick up new YAML files without restart.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Atomic skills state (prevents race conditions in async context)
# ---------------------------------------------------------------------------

_VALID_STEP_TYPES = frozenset({"agent", "tool", "condition", "human"})


@dataclass(frozen=True)
class _SkillsState:
    """Immutable skills cache — atomically swapped on load."""

    skills_by_system: dict[str, list[dict]] = field(default_factory=dict)
    loaded: bool = False


_skills_state: _SkillsState = _SkillsState()


# Generic fallback skills — ensures basic functionality even without YAML files
_DEFAULT_SKILLS: dict[str, list[dict]] = {
    "_default": [
        {
            "name": "content_pipeline",
            "triggers": [
                "write a post",
                "create content",
                "draft article",
                "blog post",
                "newsletter",
                "social media post",
                "write email",
                "write copy",
            ],
            "pipeline": ["writer", "reviewer"],
            "task_type": "content",
            "description": "Content creation with quality review",
        },
        {
            "name": "research_workflow",
            "triggers": [
                "research",
                "analyze",
                "compare",
                "investigate",
                "market analysis",
                "competitive analysis",
                "due diligence",
            ],
            "pipeline": ["analyst"],
            "task_type": "research",
            "description": "Research and analysis workflow",
        },
        {
            "name": "strategy_session",
            "triggers": [
                "strategic analysis",
                "business model",
                "positioning",
                "market opportunity",
                "growth strategy",
            ],
            "pipeline": ["analyst", "reviewer"],
            "task_type": "strategy",
            "description": "Strategic analysis with review",
        },
    ],
}


# ---------------------------------------------------------------------------
# YAML parsing and validation
# ---------------------------------------------------------------------------


def _validate_v2_skill(skill: dict) -> bool:
    """Validate v2 skill schema. Returns True if valid, False otherwise."""
    skill_name = skill.get("name", "unnamed")
    steps = skill.get("steps", [])

    if not isinstance(steps, list):
        logger.warning(f"Skill '{skill_name}': 'steps' must be a list, got {type(steps).__name__}")
        return False

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            logger.warning(f"Skill '{skill_name}' step {i}: must be a dict")
            return False
        if "id" not in step:
            logger.warning(f"Skill '{skill_name}' step {i}: missing required 'id' field")
            return False
        step_type = step.get("type", "agent")
        if step_type not in _VALID_STEP_TYPES:
            logger.warning(
                f"Skill '{skill_name}' step {i}: unknown type '{step_type}' "
                f"(valid: {', '.join(sorted(_VALID_STEP_TYPES))})"
            )
            return False

    return True


def _parse_skill_file(yaml_file: Path) -> dict | None:
    """Parse a single YAML skill file. Returns skill dict or None on failure."""
    try:
        import yaml
    except ImportError:
        return None

    try:
        with open(yaml_file, encoding="utf-8-sig") as f:
            skill = yaml.safe_load(f)

        if not (skill and isinstance(skill, dict) and "name" in skill):
            return None

        # Auto-detect v1 vs v2
        if "steps" in skill:
            skill["_version"] = 2
            if not _validate_v2_skill(skill):
                logger.warning(f"Skipping invalid v2 skill from {yaml_file}")
                return None
        else:
            skill["_version"] = 1

        skill["_source"] = str(yaml_file)
        return skill
    except Exception as e:
        logger.warning(f"Failed to load skill from {yaml_file}: {e}")
        return None


# ---------------------------------------------------------------------------
# Skill loading
# ---------------------------------------------------------------------------


def _load_yaml_skills(skills_dir: Path) -> dict[str, list[dict]]:
    """
    Load skills from YAML files organized by system directory.

    Expected structure:
        skills_dir/
            system_key_1/
                skill_a.yaml
                skill_b.yaml
            system_key_2/
                skill_c.yaml
            shared/
                skill_d.yaml
    """
    skills_by_system: dict[str, list[dict]] = {}

    if not skills_dir.exists():
        logger.warning(f"Skills directory not found: {skills_dir}")
        return skills_by_system

    for system_dir in skills_dir.iterdir():
        if not system_dir.is_dir():
            continue
        system_key = system_dir.name
        system_skills = []

        for yaml_file in system_dir.glob("*.yaml"):
            skill = _parse_skill_file(yaml_file)
            if skill:
                system_skills.append(skill)
                logger.debug(f"Loaded skill: {skill['name']} from {yaml_file}")

        # Only store non-empty lists (fixes P0-2: empty dirs suppressing defaults)
        if system_skills:
            skills_by_system[system_key] = system_skills

    return skills_by_system


def load_skills(skills_dir: Path | str = None, kb_path: Path = None):
    """
    Load all skills from YAML files + defaults.

    Builds the complete skills dict locally, then atomically swaps it in
    to prevent race conditions with concurrent readers.

    Args:
        skills_dir: Path to skills directory. If None, auto-detect from config.
        kb_path: Knowledge base path (for finding system-specific skills in R-routines/).
    """
    global _skills_state

    new_skills: dict[str, list[dict]] = {}

    # Load from dedicated skills directory
    if skills_dir:
        skills_dir_path = Path(skills_dir) if isinstance(skills_dir, str) else skills_dir
        yaml_skills = _load_yaml_skills(skills_dir_path)
        new_skills.update(yaml_skills)

    # Also load from each system's R-routines/skills/ directory
    if kb_path:
        for system_dir in kb_path.glob("systems/*/R-routines/skills"):
            if system_dir.exists():
                system_key = system_dir.parent.parent.name
                for yaml_file in system_dir.glob("*.yaml"):
                    skill = _parse_skill_file(yaml_file)
                    if skill:
                        new_skills.setdefault(system_key, []).append(skill)

    # Atomic swap — single assignment replaces entire state
    _skills_state = _SkillsState(skills_by_system=new_skills, loaded=True)

    total = sum(len(v) for v in new_skills.values())
    logger.info(f"Loaded {total} skills across {len(new_skills)} systems")


def reload_skills(skills_dir: Path | str = None, kb_path: Path = None):
    """Hot-reload skills from YAML files."""
    load_skills(skills_dir=skills_dir, kb_path=kb_path)


def get_skills_for_system(system_key: str, kb_path: Path = None) -> list[dict]:
    """
    Return the currently available skills for a system.

    Includes system-specific skills, shared skills, and fallback defaults when no
    YAML skills are loaded for the requested system.
    """
    # Take local reference for safe concurrent reads
    state = _skills_state
    if not state.loaded:
        load_skills(kb_path=kb_path)
        state = _skills_state

    skills = []
    if system_key in state.skills_by_system:
        skills.extend(state.skills_by_system[system_key])
    if "shared" in state.skills_by_system:
        skills.extend(state.skills_by_system["shared"])
    if "_shared" in state.skills_by_system:
        skills.extend(state.skills_by_system["_shared"])

    if not skills:
        skills.extend(_DEFAULT_SKILLS.get(system_key, []))
        skills.extend(_DEFAULT_SKILLS.get("_default", []))

    return list(skills)


# ---------------------------------------------------------------------------
# Skill detection with specificity scoring
# ---------------------------------------------------------------------------


def _score_trigger(trigger: str, msg_lower: str) -> int:
    """Score a single trigger against a message.

    Scoring rules:
    - Single-word triggers: word-boundary match (avoids "analyze" matching "overanalyze")
    - Multi-word triggers: substring match with specificity bonus (longer = higher score)
    - Multi-word fuzzy match: all words present but not as exact substring
    """
    trigger_lower = trigger.lower()
    words = trigger_lower.split()
    word_count = len(words)

    if word_count == 1:
        # Single-word: use word-boundary matching to avoid partial matches
        if re.search(r"\b" + re.escape(trigger_lower) + r"\b", msg_lower):
            return 8  # Word-boundary match for single words
        return 0

    # Multi-word triggers: exact substring match scores higher for longer triggers
    if trigger_lower in msg_lower:
        return 5 + (word_count * 3)  # e.g., "write a post" (3 words) = 14

    # Fuzzy: all words present in message but not as exact phrase
    if all(w in msg_lower for w in words):
        return 2 + (word_count * 2)  # e.g., "write a post" fuzzy = 8

    return 0


def detect_skill(
    message: str,
    system_key: str = None,
    kb_path: Path = None,
    return_all: bool = False,
) -> dict | list[dict] | None:
    """
    Detect if a message triggers a skill.

    Args:
        message: User's message text.
        system_key: Which system to check skills for.
        kb_path: Knowledge base path for loading skills from R-routines/skills/.
        return_all: If True, return all matching skills with scores (for debugging/dry-run).

    Returns:
        Best matching skill dict, or None if no skill matches.
        If return_all=True, returns list of (skill, score) tuples sorted by score desc.
    """
    msg_lower = message.lower()

    # Get candidate skills: system-specific + shared + defaults
    candidates = get_skills_for_system(system_key or "", kb_path=kb_path)

    # Score each skill
    scored_skills: list[tuple[dict, int]] = []

    for skill in candidates:
        score = 0
        triggers = skill.get("triggers", [])
        negative_triggers = skill.get("negative_triggers", [])

        # Check negative triggers (configurable penalty per skill)
        neg_penalty = skill.get("negative_weight", -10)
        if any(neg.lower() in msg_lower for neg in negative_triggers):
            score += neg_penalty

        # Score positive triggers with specificity weighting
        for trigger in triggers:
            score += _score_trigger(trigger, msg_lower)

        # Apply skill-level priority bonus for tie-breaking
        score += skill.get("priority", 0)

        if score > 0:
            scored_skills.append((skill, score))

    if return_all:
        scored_skills.sort(key=lambda x: -x[1])
        return scored_skills

    if not scored_skills:
        return None

    # Return the highest-scoring skill
    best_skill, best_score = max(scored_skills, key=lambda x: x[1])

    logger.info(
        f"Detected skill: {best_skill['name']} (score={best_score}) for system={system_key}"
    )
    return best_skill
