"""
Shared message utilities for RealizeOS channels.

Provides message splitting and formatting helpers used across
multiple channel adapters (Telegram, WhatsApp, etc.).
"""

import logging

logger = logging.getLogger(__name__)


def split_message(text: str, max_len: int = 4096) -> list[str]:
    """
    Split a long message into chunks that respect word and line boundaries.

    Splitting priority:
    1. Break at newline if possible (within first half of max_len..max_len)
    2. Break at space if no good newline found
    3. Hard-split at max_len as last resort

    Args:
        text: The message text to split.
        max_len: Maximum length per chunk (default: 4096, Telegram/WhatsApp limit).

    Returns:
        List of text chunks, each at most max_len characters.
    """
    if not text:
        return [""]

    if len(text) <= max_len:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Try to break at a newline within the allowed range
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            # No good newline break — try breaking at last space
            split_at = text.rfind(" ", 0, max_len)
        if split_at < max_len // 2:
            # No good space break either — hard split
            split_at = max_len

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    return chunks
