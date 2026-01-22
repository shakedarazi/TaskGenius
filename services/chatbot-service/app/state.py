# app/state.py
from typing import Optional, List, Dict, Tuple
import re
from app.constants import STATE_MARKER_PATTERN

def get_last_state_marker(conversation_history: Optional[List[Dict[str, str]]]) -> Optional[str]:
    if not conversation_history:
        return None
    for msg in reversed(conversation_history):
        content = msg.get("content", "") or ""
        markers = re.findall(STATE_MARKER_PATTERN, content)
        if markers:
            return markers[-1]
    return None

def infer_create_state_from_history(conversation_history: Optional[List[Dict[str, str]]]) -> str:
    marker = get_last_state_marker(conversation_history) or ""
    if "[[STATE:CREATE:ASK_DEADLINE]]" in marker:
        return "ASK_DEADLINE"
    if "[[STATE:CREATE:ASK_PRIORITY]]" in marker:
        return "ASK_PRIORITY"
    if "[[STATE:CREATE:ASK_TITLE]]" in marker:
        return "ASK_TITLE"
    return "INITIAL"

def infer_delete_state_from_history(conversation_history: Optional[List[Dict[str, str]]]) -> str:
    marker = get_last_state_marker(conversation_history) or ""
    if "[[STATE:DELETE:ASK_CONFIRMATION]]" in marker:
        return "ASK_CONFIRMATION"
    if "[[STATE:DELETE:SELECT_TASK]]" in marker:
        return "SELECT_TASK"
    if "[[STATE:DELETE:IDENTIFY_TASK]]" in marker:
        return "IDENTIFY_TASK"
    return "IDENTIFY_TASK"

def infer_update_state_from_history(conversation_history: Optional[List[Dict[str, str]]]) -> Tuple[str, Optional[str]]:
    marker = get_last_state_marker(conversation_history) or ""
    if "[[STATE:UPDATE:ASK_CONFIRMATION]]" in marker:
        return ("ASK_CONFIRMATION", None)

    m = re.search(r"\[\[STATE:UPDATE:ASK_VALUE:(\w+)\]\]", marker)
    if m:
        return ("ASK_VALUE", m.group(1))

    if "[[STATE:UPDATE:ASK_FIELD]]" in marker:
        return ("ASK_FIELD", None)
    if "[[STATE:UPDATE:SELECT_TASK]]" in marker:
        return ("SELECT_TASK", None)
    if "[[STATE:UPDATE:IDENTIFY_TASK]]" in marker:
        return ("IDENTIFY_TASK", None)

    return ("IDENTIFY_TASK", None)
def infer_query_state_from_history(conversation_history: Optional[List[Dict[str, str]]]) -> str:
    marker = get_last_state_marker(conversation_history) or ""
    if "[[STATE:QUERY:SHOW_RESULTS]]" in marker:
        return "SHOW_RESULTS"
    if "[[STATE:QUERY:ASK_CRITERIA]]" in marker:
        return "ASK_CRITERIA"
    return "ASK_CRITERIA"