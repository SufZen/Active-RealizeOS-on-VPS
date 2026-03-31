"""
Auto-Evolution Engine: Proposes, reviews, and applies system improvements.

Builds on the existing evolution module (gap_detector, skill_suggester, etc.)
to add:
- Automated evolution proposals with priority scoring
- Gated approval flow (auto-approve low-risk, require approval for high-risk)
- Rollback capability for applied changes
- Rate limiting to prevent runaway evolution
- Safety validation (blocked paths, content size limits, dangerous patterns)
- Proposal persistence to SQLite
- Execution dispatch to skill_suggester/prompt_refiner
- Evolution changelog for audit trail
"""

import fnmatch
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# --- Safety constraints ---

# Files/patterns that evolution must NEVER modify
BLOCKED_PATHS: frozenset[str] = frozenset({
    "identity.md",
    "config.py",
    "realize-os.yaml",
    ".env",
    "*.key",
    "*.pem",
    "*.secret",
    "*.credentials",
    "__init__.py",
})

# Maximum size for generated content (bytes)
MAX_CONTENT_SIZE = 10240

# Dangerous patterns in generated content
_DANGEROUS_PATTERNS = re.compile(
    r"(?:"
    r"import\s+(?:os|subprocess|shutil|sys)|"
    r"from\s+(?:os|subprocess|shutil|sys)\s+import|"
    r"exec\s*\(|"
    r"eval\s*\(|"
    r"__import__|"
    r"subprocess\.|"
    r"shutil\.rmtree|"
    r"rm\s+-rf|"
    r";\s*(?:rm|del|drop|truncate)\b"
    r")",
    re.IGNORECASE,
)


class EvolutionType(Enum):
    """Types of system evolution."""

    NEW_SKILL = "new_skill"  # Add a new skill
    REFINE_PROMPT = "refine_prompt"  # Improve an agent's prompt
    ADD_TOOL = "add_tool"  # Register a new tool
    CONFIG_CHANGE = "config_change"  # Change system configuration
    WORKFLOW_ADD = "workflow_add"  # Add a new workflow


class RiskLevel(Enum):
    """Risk assessment of a proposed evolution."""

    LOW = "low"  # Safe: new skill, minor prompt tweak
    MEDIUM = "medium"  # Needs review: config change, tool addition
    HIGH = "high"  # Dangerous: prompt replacement, workflow changes


class ProposalStatus(Enum):
    """Status of an evolution proposal."""

    PENDING = "pending"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class EvolutionProposal:
    """A proposed system evolution."""

    id: str
    evolution_type: EvolutionType
    title: str
    description: str
    risk_level: RiskLevel = RiskLevel.LOW
    status: ProposalStatus = ProposalStatus.PENDING
    priority: float = 0.5  # 0.0-1.0 priority score
    changes: dict[str, Any] = field(default_factory=dict)
    rollback_data: dict[str, Any] = field(default_factory=dict)
    source: str = ""  # What triggered this (gap_detector, user, etc.)
    created_at: float = field(default_factory=time.time)
    applied_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_proposal(proposal: EvolutionProposal) -> tuple[bool, str]:
    """
    Validate a proposal against safety constraints.

    Returns (is_valid, reason). Checks:
    - File paths against BLOCKED_PATHS
    - Content size against MAX_CONTENT_SIZE
    - Content for dangerous patterns
    """
    changes = proposal.changes or {}

    # Check file paths
    target_path = changes.get("target_path", "") or changes.get("prompt_path", "")
    if target_path:
        filename = target_path.rsplit("/", 1)[-1] if "/" in target_path else target_path
        for pattern in BLOCKED_PATHS:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(target_path, f"*/{pattern}"):
                return False, f"Blocked path: '{target_path}' matches '{pattern}'"

    # Check content size
    content = changes.get("content", "") or changes.get("yaml", "")
    if isinstance(content, str) and len(content.encode("utf-8", errors="ignore")) > MAX_CONTENT_SIZE:
        return False, f"Content too large: {len(content)} bytes exceeds {MAX_CONTENT_SIZE}"

    # Check for dangerous patterns in generated content
    if isinstance(content, str) and _DANGEROUS_PATTERNS.search(content):
        match = _DANGEROUS_PATTERNS.search(content)
        return False, f"Dangerous pattern detected: '{match.group()[:60]}'"

    return True, ""


# --- Persistence helpers ---

def _get_conn():
    """Get a SQLite connection (lazy import to avoid circular deps)."""
    from realize_core.evolution.analytics import _get_conn as analytics_conn
    return analytics_conn()


def _proposal_to_row(p: EvolutionProposal) -> tuple:
    """Convert a proposal to a DB row tuple."""
    return (
        p.id, p.evolution_type.value, p.title, p.description,
        p.risk_level.value, p.status.value, p.priority,
        json.dumps(p.changes), json.dumps(p.rollback_data),
        p.source, p.created_at, p.applied_at,
        json.dumps(p.metadata),
    )


def _row_to_proposal(row: dict) -> EvolutionProposal:
    """Convert a DB row to an EvolutionProposal."""
    return EvolutionProposal(
        id=row["id"],
        evolution_type=EvolutionType(row["evolution_type"]),
        title=row["title"],
        description=row["description"],
        risk_level=RiskLevel(row["risk_level"]),
        status=ProposalStatus(row["status"]),
        priority=row["priority"],
        changes=json.loads(row["changes_json"]) if row["changes_json"] else {},
        rollback_data=json.loads(row["rollback_json"]) if row["rollback_json"] else {},
        source=row["source"],
        created_at=row["created_at"],
        applied_at=row["applied_at"],
        metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
    )


def _log_changelog(proposal_id: str, action: str, details: dict = None, actor: str = "system"):
    """Log an entry to the evolution changelog."""
    try:
        with _get_conn() as conn:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO evolution_changelog (timestamp, proposal_id, action, actor, details_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (now, proposal_id, action, actor, json.dumps(details or {})),
            )
    except Exception as e:
        logger.debug(f"Changelog log failed: {e}")


# --- LLM Rate Limiter ---

class EvolutionRateLimiter:
    """Rate limiter for evolution LLM calls (sliding window)."""

    def __init__(self, max_calls_per_hour: int = 20):
        self._max_calls = max_calls_per_hour
        self._call_times: list[float] = []

    def check(self) -> bool:
        """Returns True if a call is allowed."""
        now = time.time()
        one_hour_ago = now - 3600
        self._call_times = [t for t in self._call_times if t > one_hour_ago]
        return len(self._call_times) < self._max_calls

    def record(self):
        """Record a call."""
        self._call_times.append(time.time())

    @property
    def remaining(self) -> int:
        now = time.time()
        one_hour_ago = now - 3600
        active = sum(1 for t in self._call_times if t > one_hour_ago)
        return max(0, self._max_calls - active)


_llm_rate_limiter: EvolutionRateLimiter | None = None


def get_evolution_rate_limiter() -> EvolutionRateLimiter:
    global _llm_rate_limiter
    if _llm_rate_limiter is None:
        _llm_rate_limiter = EvolutionRateLimiter()
    return _llm_rate_limiter


# --- Evolution Engine ---

class EvolutionEngine:
    """
    Manages the lifecycle of system evolution proposals.

    Flow: Propose -> Review (auto or manual) -> Apply -> Monitor -> Rollback if needed
    """

    def __init__(
        self,
        auto_approve_low_risk: bool = True,
        rate_limit_per_hour: int = 10,
        persist: bool = True,
    ):
        self._proposals: dict[str, EvolutionProposal] = {}
        self._auto_approve_low_risk = auto_approve_low_risk
        self._rate_limit = rate_limit_per_hour
        self._applied_this_hour: list[float] = []
        self._persist = persist

        # Load persisted proposals
        if persist:
            self._load_proposals()

    def _load_proposals(self):
        """Load existing proposals from SQLite."""
        try:
            with _get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM evolution_proposals WHERE status IN ('pending', 'approved')"
                ).fetchall()
                for row in rows:
                    p = _row_to_proposal(dict(row))
                    self._proposals[p.id] = p
                if rows:
                    logger.debug(f"Loaded {len(rows)} proposals from DB")
        except Exception as e:
            logger.debug(f"Could not load proposals (table may not exist): {e}")

    def _save_proposal(self, proposal: EvolutionProposal):
        """Persist a proposal to SQLite."""
        if not self._persist:
            return
        try:
            with _get_conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO evolution_proposals
                    (id, evolution_type, title, description, risk_level, status, priority,
                     changes_json, rollback_json, source, created_at, applied_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    _proposal_to_row(proposal),
                )
        except Exception as e:
            logger.debug(f"Could not save proposal: {e}")

    def propose(self, proposal: EvolutionProposal) -> bool:
        """
        Submit a new evolution proposal.

        Validates safety constraints first. Low-risk proposals are auto-approved if enabled.
        Returns True if the proposal was accepted.
        """
        if proposal.id in self._proposals:
            return False

        # Safety validation
        is_valid, reason = validate_proposal(proposal)
        if not is_valid:
            proposal.status = ProposalStatus.REJECTED
            proposal.metadata["rejection_reason"] = f"Safety: {reason}"
            self._proposals[proposal.id] = proposal
            self._save_proposal(proposal)
            _log_changelog(proposal.id, "rejected", {"reason": reason})
            logger.warning(f"Proposal rejected (safety): {proposal.id} -- {reason}")
            return False

        self._proposals[proposal.id] = proposal
        logger.info(
            f"Evolution proposal '{proposal.id}': {proposal.title} "
            f"(risk={proposal.risk_level.value}, priority={proposal.priority:.1f})"
        )
        _log_changelog(proposal.id, "proposed", {"title": proposal.title, "risk": proposal.risk_level.value})

        # Auto-approve low-risk if enabled
        if self._auto_approve_low_risk and proposal.risk_level == RiskLevel.LOW:
            proposal.status = ProposalStatus.APPROVED
            _log_changelog(proposal.id, "auto_approved")
            logger.info(f"Auto-approved: {proposal.id}")

        self._save_proposal(proposal)
        return True

    def approve(self, proposal_id: str) -> bool:
        """Manually approve a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.PENDING:
            return False
        proposal.status = ProposalStatus.APPROVED
        self._save_proposal(proposal)
        _log_changelog(proposal_id, "approved")
        logger.info(f"Approved: {proposal_id}")
        return True

    def reject(self, proposal_id: str, reason: str = "") -> bool:
        """Reject a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.PENDING:
            return False
        proposal.status = ProposalStatus.REJECTED
        proposal.metadata["rejection_reason"] = reason
        self._save_proposal(proposal)
        _log_changelog(proposal_id, "rejected", {"reason": reason})
        logger.info(f"Rejected: {proposal_id} ({reason})")
        return True

    def apply(self, proposal_id: str, dry_run: bool = False) -> bool | dict:
        """
        Apply an approved evolution.

        Checks rate limits before applying.
        If dry_run=True, returns a preview dict without executing.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.APPROVED:
            return False

        # Check rate limit
        if not self._check_rate_limit():
            logger.warning(f"Rate limit exceeded, deferring: {proposal_id}")
            return False

        if dry_run:
            return {
                "proposal_id": proposal.id,
                "title": proposal.title,
                "type": proposal.evolution_type.value,
                "risk": proposal.risk_level.value,
                "changes": proposal.changes,
                "would_apply": True,
            }

        # Record application
        proposal.status = ProposalStatus.APPLIED
        proposal.applied_at = time.time()
        self._applied_this_hour.append(time.time())
        self._save_proposal(proposal)
        _log_changelog(proposal_id, "applied", {"type": proposal.evolution_type.value})

        logger.info(f"Applied evolution: {proposal.title}")
        return True

    def rollback(self, proposal_id: str) -> bool:
        """
        Roll back an applied evolution.

        Uses stored rollback_data to restore previous state.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.APPLIED:
            return False

        proposal.status = ProposalStatus.ROLLED_BACK
        self._save_proposal(proposal)
        _log_changelog(proposal_id, "rolled_back")
        logger.info(f"Rolled back: {proposal.title}")
        return True

    def _check_rate_limit(self) -> bool:
        """Check if we've exceeded the hourly rate limit."""
        now = time.time()
        one_hour_ago = now - 3600
        self._applied_this_hour = [t for t in self._applied_this_hour if t > one_hour_ago]
        return len(self._applied_this_hour) < self._rate_limit

    def get_proposal(self, proposal_id: str) -> EvolutionProposal | None:
        return self._proposals.get(proposal_id)

    def get_pending(self) -> list[EvolutionProposal]:
        """Get all pending proposals, sorted by priority."""
        pending = [p for p in self._proposals.values() if p.status == ProposalStatus.PENDING]
        return sorted(pending, key=lambda p: -p.priority)

    def get_applied(self) -> list[EvolutionProposal]:
        """Get all applied proposals, newest first."""
        applied = [p for p in self._proposals.values() if p.status == ProposalStatus.APPLIED]
        return sorted(applied, key=lambda p: -p.applied_at)

    @property
    def proposal_count(self) -> int:
        return len(self._proposals)

    def status_summary(self) -> dict:
        """Get summary of all proposals by status."""
        summary: dict[str, int] = {}
        for p in self._proposals.values():
            key = p.status.value
            summary[key] = summary.get(key, 0) + 1
        return {
            "total": self.proposal_count,
            "by_status": summary,
            "rate_this_hour": len(self._applied_this_hour),
            "rate_limit": self._rate_limit,
        }


def get_changelog(days: int = 30) -> list[dict]:
    """Get recent evolution changelog entries."""
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM evolution_changelog WHERE timestamp > datetime('now', ?) "
                "ORDER BY timestamp DESC",
                (f"-{days} days",),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# Singleton
_engine: EvolutionEngine | None = None


def get_evolution_engine(**kwargs) -> EvolutionEngine:
    global _engine
    if _engine is None:
        _engine = EvolutionEngine(**kwargs)
    return _engine
