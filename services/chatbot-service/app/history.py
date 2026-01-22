# app/history.py
from __future__ import annotations

from typing import Dict, List, Optional


def find_last_assistant_index_with_marker(
    conversation_history: Optional[List[Dict[str, str]]],
    marker: str
) -> Optional[int]:
    """
    Returns the index of the LAST assistant message whose content contains `marker`.
    """
    if not conversation_history:
        return None

    for i in range(len(conversation_history) - 1, -1, -1):
        msg = conversation_history[i]
        if msg.get("role") == "assistant" and marker in (msg.get("content", "") or ""):
            return i
    return None


def find_previous_user_message(
    before_index: int,
    conversation_history: List[Dict[str, str]]
) -> Optional[str]:
    """
    Walk backwards from before_index-1 and return the first user message content.
    """
    for i in range(before_index - 1, -1, -1):
        if conversation_history[i].get("role") == "user":
            return (conversation_history[i].get("content", "") or "").strip()
    return None


def find_user_message_after_marker(
    conversation_history: Optional[List[Dict[str, str]]],
    marker: str
) -> Optional[str]:
    """
    Returns the FIRST user message immediately after the LAST assistant message containing `marker`.
    """
    if not conversation_history:
        return None

    for i in range(len(conversation_history) - 1, -1, -1):
        msg = conversation_history[i]
        if msg.get("role") == "assistant" and marker in (msg.get("content", "") or ""):
            if i + 1 < len(conversation_history):
                next_msg = conversation_history[i + 1]
                if next_msg.get("role") == "user":
                    content = (next_msg.get("content", "") or "").strip()
                    return content or None
            return None

    return None
