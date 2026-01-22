# app/confirm.py
from dataclasses import dataclass
from typing import Set
import re

from app.constants import CONFIRM_TOKENS, CANCEL_TOKENS

@dataclass(frozen=True)
class ConfirmationResult:
    confirmed: bool
    cancelled: bool

def normalize_confirmation_text(text: str) -> list[str]:
    if not text:
        return []
    s = text.strip().lower()
    s = re.sub(r"[^\w\u0590-\u05FF\s]", " ", s)  # remove punctuation, keep hebrew/english
    s = re.sub(r"\s+", " ", s).strip()
    return s.split(" ") if s else []

def parse_confirmation(text: str,
                       confirm_tokens: Set[str] = CONFIRM_TOKENS,
                       cancel_tokens: Set[str] = CANCEL_TOKENS) -> ConfirmationResult:
    tokens = normalize_confirmation_text(text)
    has_confirm = any(t in confirm_tokens for t in tokens)
    has_cancel = any(t in cancel_tokens for t in tokens)

    # Safer default: if both appear, treat as cancel
    confirmed = has_confirm and not has_cancel
    cancelled = has_cancel and not has_confirm
    return ConfirmationResult(confirmed=confirmed, cancelled=cancelled)
