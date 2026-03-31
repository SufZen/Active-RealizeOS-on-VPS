"""
Gap Detection: Analyze interaction logs to find capability gaps.

Identifies:
1. Unhandled requests -- no tool or skill matched action intents
2. Repeated patterns -- same type of request done ad-hoc 3+ times
3. Failed tool calls -- tools that error repeatedly
4. Low satisfaction -- corrections, retries, negative feedback

Outputs structured "evolution suggestions" to the suggestions table.
"""

import hashlib
import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from realize_core.evolution.analytics import _get_conn, get_interactions_for_analysis

logger = logging.getLogger(__name__)


@dataclass
class GapDetectionConfig:
    """Configurable thresholds for gap detection."""

    unhandled_threshold: int = 3
    tool_failure_threshold: int = 3  # raised from 2 to filter transient errors
    low_satisfaction_threshold: int = 3
    repeated_pattern_threshold: int = 3
    min_confidence: float = 0.6


_DEFAULT_CONFIG = GapDetectionConfig()


async def run_gap_analysis(days: int = 7, config: GapDetectionConfig = None) -> list[dict]:
    """
    Analyze recent interactions and generate evolution suggestions.

    Returns list of suggestion dicts.
    """
    config = config or _DEFAULT_CONFIG
    suggestions = []

    # Expire stale pending suggestions (older than 30 days)
    _expire_stale_suggestions()

    interactions = get_interactions_for_analysis(days=days, limit=500)
    if not interactions:
        return suggestions

    total_count = len(interactions)
    suggestions.extend(_detect_unhandled_requests(interactions, config, total_count))
    suggestions.extend(_detect_repeated_patterns(interactions, config, total_count))
    suggestions.extend(_detect_tool_failures(interactions, config, total_count))
    suggestions.extend(_detect_low_satisfaction(interactions, config, total_count))

    if suggestions:
        stored = _store_suggestions(suggestions)
        _create_evolution_proposals(suggestions)
        logger.info(f"Gap analysis complete: {len(suggestions)} found, {stored} new stored")

    return suggestions


def _expire_stale_suggestions():
    """Expire pending suggestions older than 30 days."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE evolution_suggestions SET status = 'expired' "
                "WHERE status = 'pending' AND timestamp < datetime('now', '-30 days')"
            )
    except Exception as e:
        logger.debug(f"Suggestion expiry failed (non-fatal): {e}")


def _compute_suggestion_hash(suggestion_type: str, title: str) -> str:
    """Compute a content hash for deduplication."""
    content = f"{suggestion_type}:{title}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _detect_unhandled_requests(
    interactions: list[dict], config: GapDetectionConfig, total_count: int
) -> list[dict]:
    """Find interactions where the system likely couldn't fulfill the request."""
    suggestions = []
    unhandled = []

    for ix in interactions:
        if ix.get("error"):
            unhandled.append(ix["message_preview"])
            continue
        tools = json.loads(ix.get("tools_used", "[]"))
        if not tools and not ix.get("skill_name") and ix.get("intent") in ("research", "act"):
            unhandled.append(ix["message_preview"])

    if len(unhandled) >= config.unhandled_threshold:
        confidence = min(len(unhandled) / max(total_count, 1), 1.0)
        if confidence >= config.min_confidence:
            samples = unhandled[:10]
            suggestions.append(
                {
                    "type": "unhandled_requests",
                    "title": f"{len(unhandled)} potentially unhandled requests",
                    "description": (
                        f"Found {len(unhandled)} requests that may not have been fully addressed. "
                        f"Samples: {'; '.join(t[:60] for t in samples[:3])}"
                    ),
                    "confidence": round(confidence, 2),
                    "action_data": {"samples": samples},
                }
            )

    return suggestions


def _detect_repeated_patterns(
    interactions: list[dict], config: GapDetectionConfig, total_count: int
) -> list[dict]:
    """Find repeated ad-hoc requests that could become skills."""
    suggestions = []
    adhoc_types = Counter()
    adhoc_samples = {}

    for ix in interactions:
        if not ix.get("skill_name") and ix.get("task_type"):
            task_type = ix["task_type"]
            adhoc_types[task_type] += 1
            if task_type not in adhoc_samples:
                adhoc_samples[task_type] = []
            if len(adhoc_samples[task_type]) < 5:
                adhoc_samples[task_type].append(ix["message_preview"])

    for task_type, count in adhoc_types.most_common(5):
        if count >= config.repeated_pattern_threshold:
            confidence = min(count / max(total_count, 1) * 5, 1.0)  # scale up for repeated patterns
            if confidence >= config.min_confidence:
                suggestions.append(
                    {
                        "type": "repeated_pattern",
                        "title": f"'{task_type}' requested {count} times without a skill",
                        "description": (
                            f"The task type '{task_type}' was triggered {count} times "
                            f"without matching any skill. Consider creating a skill for this."
                        ),
                        "confidence": round(confidence, 2),
                        "action_data": {
                            "task_type": task_type,
                            "count": count,
                            "samples": adhoc_samples.get(task_type, []),
                        },
                    }
                )

    return suggestions


def _detect_tool_failures(
    interactions: list[dict], config: GapDetectionConfig, total_count: int
) -> list[dict]:
    """Find tools that fail repeatedly."""
    suggestions = []
    error_tools = Counter()
    for ix in interactions:
        if ix.get("error"):
            for tool in json.loads(ix.get("tools_used", "[]")):
                error_tools[tool] += 1

    for tool, count in error_tools.most_common(3):
        if count >= config.tool_failure_threshold:
            confidence = min(count / max(total_count, 1) * 10, 1.0)
            suggestions.append(
                {
                    "type": "tool_failure",
                    "title": f"Tool '{tool}' failed {count} times",
                    "description": f"The tool '{tool}' has encountered errors {count} times. Check configuration.",
                    "confidence": round(confidence, 2),
                    "action_data": {"tool": tool, "error_count": count},
                }
            )

    return suggestions


def _detect_low_satisfaction(
    interactions: list[dict], config: GapDetectionConfig, total_count: int
) -> list[dict]:
    """Find areas with low satisfaction signals."""
    suggestions = []
    # Weighted scoring: negative signals are stronger indicators
    signal_weights = {
        "negative": 1.0,
        "correction": 0.8,
        "retry": 0.5,
    }
    system_scores: dict[str, float] = {}
    system_counts: dict[str, int] = {}

    for ix in interactions:
        signal = ix.get("satisfaction_signal", "")
        weight = signal_weights.get(signal, 0)
        if weight > 0:
            system = ix["system_key"]
            system_scores[system] = system_scores.get(system, 0) + weight
            system_counts[system] = system_counts.get(system, 0) + 1

    # Sort by weighted score descending
    for system, score in sorted(system_scores.items(), key=lambda x: -x[1])[:3]:
        raw_count = system_counts.get(system, 0)
        if raw_count >= config.low_satisfaction_threshold:
            confidence = min(score / max(total_count, 1) * 5, 1.0)
            suggestions.append(
                {
                    "type": "low_satisfaction",
                    "title": f"{system}: {raw_count} negative satisfaction signals (weighted: {score:.1f})",
                    "description": (
                        f"System '{system}' received {raw_count} negative signals "
                        f"(weighted score: {score:.1f}). "
                        f"Review recent interactions for improvement areas."
                    ),
                    "confidence": round(confidence, 2),
                    "action_data": {"system_key": system, "signal_count": raw_count, "weighted_score": score},
                }
            )

    return suggestions


def _store_suggestions(suggestions: list[dict]) -> int:
    """Store evolution suggestions in the database. Returns count of new suggestions stored."""
    stored = 0
    with _get_conn() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for s in suggestions:
            content_hash = _compute_suggestion_hash(s["type"], s["title"])

            # Deduplication: skip if a pending suggestion with the same hash exists
            existing = conn.execute(
                "SELECT id FROM evolution_suggestions WHERE content_hash = ? AND status = 'pending'",
                (content_hash,),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                """
                INSERT INTO evolution_suggestions
                (timestamp, suggestion_type, title, description, action_data, status, content_hash)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
                (now, s["type"], s["title"], s["description"], json.dumps(s.get("action_data", {})), content_hash),
            )
            stored += 1
    return stored


def _create_evolution_proposals(suggestions: list[dict]):
    """Bridge gap detector suggestions to EvolutionEngine proposals."""
    try:
        from realize_core.evolution.engine import (
            EvolutionProposal,
            EvolutionType,
            RiskLevel,
            get_evolution_engine,
        )

        engine = get_evolution_engine()

        type_mapping = {
            "unhandled_requests": (EvolutionType.NEW_SKILL, RiskLevel.LOW),
            "repeated_pattern": (EvolutionType.NEW_SKILL, RiskLevel.LOW),
            "tool_failure": (EvolutionType.CONFIG_CHANGE, RiskLevel.MEDIUM),
            "low_satisfaction": (EvolutionType.REFINE_PROMPT, RiskLevel.MEDIUM),
        }

        for s in suggestions:
            evo_type, risk = type_mapping.get(
                s["type"], (EvolutionType.CONFIG_CHANGE, RiskLevel.MEDIUM)
            )
            proposal_id = f"gap_{_compute_suggestion_hash(s['type'], s['title'])}"
            proposal = EvolutionProposal(
                id=proposal_id,
                evolution_type=evo_type,
                title=s["title"],
                description=s["description"],
                risk_level=risk,
                priority=s.get("confidence", 0.5),
                source="gap_detector",
                changes=s.get("action_data", {}),
            )
            engine.propose(proposal)
    except Exception as e:
        logger.debug(f"Could not create evolution proposals: {e}")


def get_pending_suggestions() -> list[dict]:
    """Get all pending evolution suggestions."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM evolution_suggestions WHERE status = 'pending' ORDER BY timestamp DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_suggestion(suggestion_id: int, status: str = "approved"):
    """Mark a suggestion as approved, dismissed, or applied."""
    with _get_conn() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE evolution_suggestions SET status = ?, resolved_at = ? WHERE id = ?",
            (status, now, suggestion_id),
        )


def format_suggestions_overview(suggestions: list[dict]) -> str:
    """Format suggestions for display."""
    if not suggestions:
        return "No pending evolution suggestions. The system is running well."
    lines = [f"**Evolution Suggestions ({len(suggestions)}):**\n"]
    for s in suggestions:
        icon = {"unhandled_requests": "?", "repeated_pattern": "->", "tool_failure": "!", "low_satisfaction": "~"}.get(
            s["suggestion_type"], "*"
        )
        confidence = ""
        if "confidence" in s:
            confidence = f" [{s['confidence']:.0%}]"
        lines.append(
            f"  {icon} **#{s['id']}** [{s['suggestion_type']}]{confidence}\n    {s['title']}\n    _{s['description'][:120]}_"
        )
    return "\n".join(lines)
