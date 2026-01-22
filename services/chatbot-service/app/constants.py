# app/constants.py

# Keep these canonical values consistent with core-api enums
PRIORITY_MAP = {
    # English
    "low": "low",
    "medium": "medium",
    "high": "high",
    "urgent": "urgent",
    # Hebrew
    "נמוכה": "low",
    "בינונית": "medium",
    "גבוהה": "high",
    "דחופה": "urgent",
}

STATUS_MAP_EN = {
    "open": "open",
    "in_progress": "in_progress",
    "done": "done",
    "completed": "done",
}

STATUS_MAP_HE = {
    "פתוח": "open",
    "בביצוע": "in_progress",
    "בוצע": "done",
    "סיימתי": "done",
}

NONE_KEYWORDS = {"no", "none", "skip", "לא", "אין", "בלי", "דלג", "null"}

CONFIRM_TOKENS = {"כן", "אוקיי", "אישור", "yes", "ok", "okay", "confirm"}
CANCEL_TOKENS = {"לא", "no", "cancel", "canceled", "cancelled"}

GENERIC_UPDATE_PHRASES = {
    "update", "update task", "edit", "edit task", "change", "change task", "modify", "modify task"
}

GENERIC_DELETE_PHRASES = {
    "delete", "delete task", "remove", "remove task", "מחק", "מחק משימה", "תמחק", "הסר", "הסר משימה"
}

STATE_MARKER_PATTERN = r"\[\[STATE[^\]]+\]\]"
DATE_MARKER_PATTERN = r"\[\[DATE[^\]]+\]\]"