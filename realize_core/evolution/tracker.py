"""
Lightweight interaction tracker -- wraps analytics for use in handlers.

Also detects satisfaction signals from user messages with word-boundary
matching and negation detection to reduce false positives.
"""

import logging
import re
import time

from realize_core.evolution.analytics import log_interaction

logger = logging.getLogger(__name__)

NEGATIVE_SIGNALS = [
    "no that's wrong",
    "that's not right",
    "incorrect",
    "wrong answer",
    "not what i asked",
    "try again",
    "redo this",
    "start over",
    "that's not what i meant",
    "you misunderstood",
]

RETRY_SIGNALS = [
    "retry",
    "one more time",
    "let me rephrase",
    "what i meant was",
    "i said",
]

POSITIVE_WORDS = ["thanks", "thank you", "perfect", "great", "exactly", "good", "good job", "well done", "awesome", "excellent"]

# Negation words that flip a positive signal to correction
_NEGATION_WORDS = {"not", "no", "don't", "doesn't", "isn't", "wasn't", "never", "neither", "hardly"}

# Compile word-boundary patterns for positive words
_POSITIVE_PATTERNS = [re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE) for w in POSITIVE_WORDS]
_NEGATIVE_PATTERNS = [re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE) for p in NEGATIVE_SIGNALS]
_RETRY_PATTERNS = [re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE) for p in RETRY_SIGNALS]


def _has_preceding_negation(message_lower: str, match_start: int) -> bool:
    """Check if a negation word appears within 3 tokens before the match position."""
    # Get the text before the match
    prefix = message_lower[:match_start].strip()
    if not prefix:
        return False
    # Get last 3 tokens
    tokens = prefix.split()[-3:]
    return any(token.rstrip(".,!?;:") in _NEGATION_WORDS for token in tokens)


def detect_satisfaction_signal(message: str) -> tuple[str, float] | None:
    """
    Detect if a message indicates satisfaction (or lack thereof).

    Returns (signal, confidence) or None. Signal is one of:
    'correction', 'retry', 'positive'.

    Uses word-boundary matching and negation detection to reduce false positives.
    """
    msg_lower = message.lower()

    # Check negative signals first (highest priority, highest confidence)
    for pattern in _NEGATIVE_PATTERNS:
        if pattern.search(msg_lower):
            return ("correction", 0.9)

    # Check retry signals
    for pattern in _RETRY_PATTERNS:
        if pattern.search(msg_lower):
            return ("retry", 0.7)

    # Check positive signals with negation detection
    for pattern in _POSITIVE_PATTERNS:
        match = pattern.search(msg_lower)
        if match:
            if _has_preceding_negation(msg_lower, match.start()):
                # "not good", "no thanks" etc. -> correction, not positive
                return ("correction", 0.7)
            return ("positive", 0.6)

    return None


class InteractionTimer:
    """Context manager to time interactions and log them."""

    def __init__(self, user_id: str, system_key: str, message: str):
        self.user_id = str(user_id)
        self.system_key = system_key
        self.message = message
        self.start_time = None
        self.agent_key = ""
        self.skill_name = ""
        self.task_type = ""
        self.tools_used = []
        self.intent = ""
        self.error = ""
        self.response_length = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = int((time.time() - self.start_time) * 1000)
        if exc_val:
            self.error = str(exc_val)[:200]
        try:
            log_interaction(
                user_id=self.user_id,
                system_key=self.system_key,
                message=self.message,
                response_length=self.response_length,
                latency_ms=latency_ms,
                agent_key=self.agent_key,
                skill_name=self.skill_name,
                task_type=self.task_type,
                tools_used=self.tools_used,
                intent=self.intent,
                error=self.error,
            )
        except Exception as e:
            logger.debug(f"Interaction logging failed (non-fatal): {e}")
        return False
