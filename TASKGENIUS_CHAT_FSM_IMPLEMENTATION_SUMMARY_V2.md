# TaskGenius Chat System — Deterministic FSM Implementation Summary
## Revision v2.1 (Execution & Priority Patch)

---

## Core Architecture Principles

### 1. Determinism First


All decisions are determined by rule-based FSM logic only:
- **Intent detection**: keyword matching and state inference from explicit state markers
- **Slot filling**: field extraction from conversation history based on FSM state markers
- **Readiness**: determined by collected fields and state transitions, never by LLM judgment
- **Confirmation detection**: token matching within specific FSM states only
- **State inference**: read exclusively from explicit state markers in conversation history

**OpenAI (LLM) is NEVER used for:**
- Intent detection
- Field extraction
- Readiness decisions
- Confirmation detection
- State inference

### 2. OpenAI Usage (NLG Only)

OpenAI is used **ONLY** to rewrite the final reply text after deterministic routing.

**NLG Rewriting Requirements:**
- Preserves meaning exactly
- Preserves number of questions
- Preserves lists/options
- Preserves all FSM state markers verbatim (never removes or modifies them)
- Does not add new steps, questions, or suggestions
- Maintains the same language as the deterministic reply

**Fallback Behavior:**
- If OpenAI fails or is unavailable: return the deterministic reply unchanged
- If OpenAI rewrites fail: return the deterministic reply unchanged
- No exception is thrown; the system continues with the deterministic reply

### 3. Explicit FSM State Markers (Critical)

Every assistant message that advances a CRUD flow **MUST** include a hidden, machine-readable state marker.

**Marker Format:**
```
[[STATE:<FLOW>:<STEP>]]
```

**Examples:**
- `[[STATE:CREATE:ASK_TITLE]]`
- `[[STATE:CREATE:ASK_PRIORITY]]`
- `[[STATE:CREATE:ASK_DEADLINE]]`
- `[[STATE:DELETE:SELECT_TASK]]`
- `[[STATE:DELETE:ASK_CONFIRMATION]]`
- `[[STATE:UPDATE:SELECT_TASK]]`
- `[[STATE:UPDATE:ASK_FIELD]]`
- `[[STATE:UPDATE:ASK_VALUE:priority]]`
- `[[STATE:UPDATE:ASK_CONFIRMATION]]`

**Marker Properties:**
- Language-independent (always English, regardless of user language)
- Stored verbatim in conversation_history
- Never modified or removed by OpenAI NLG

**FSM State Inference Rule:**
- FSM state is determined by the **LAST** state marker found in conversation_history, scanning from newest to oldest (latest marker wins)
- If no marker exists: treat as new request (INITIAL state)
- Earlier markers are ignored (only the most recent marker matters)
- Never infer state from free text, keywords, or message content

### 4. Continue Active Flow Has Priority (Global Rule)

**Critical Determinism Rule:**
- If a valid FSM state marker exists in the most recent assistant message in conversation_history, the system **MUST** continue that flow and **MUST NOT** start a new intent via keyword matching, except when the user explicitly cancels (global cancel commands)

**Global Cancel Commands (per language):**
- English: `"cancel"`, `"stop"`, `"never mind"`
- Hebrew: `"בטל"`, `"עזוב"`, `"לא משנה"`

**Cancellation Behavior:**
- If global cancel command detected while in active flow (from ANY state) → reset to INITIAL state, clear flow context safely (clear `ref` and collected fields)
- After cancellation, system returns to initial state and can accept new intents via keyword matching
- **Note:** `"no"` / `"לא"` are NOT global cancel commands; they are treated as negative response only in ASK_CONFIRMATION state (see Section 6)

**Flow Continuity:**
- Active flows take precedence over keyword-based intent detection
- This ensures deterministic progression through multi-step flows without interruption from accidental keyword matches

### 5. Clarify Is a First-Class Command

When required information is missing OR task identification is ambiguous:
- Emit `command.intent = "clarify"`
- Set `command.ready = false`
- Set `command.missing_fields` to the missing information

**Core-api Execution Rules:**
- Core-api **MUST NEVER** execute any action when `command.intent == "clarify"`
- Clarify responses include:
  - Clear question in user's language
  - Up to 5 options if task matching is ambiguous (title + id for each)

**Clarify with Task Selection:**
- When ambiguous task matches occur, the system emits clarify AND includes an explicit SELECT_TASK state marker
- This ensures deterministic continuation of the flow after task selection

### 6. Confirmation Is State-Gated

Confirmation tokens are accepted **ONLY** when the current FSM state is explicitly `ASK_CONFIRMATION`.

**Accepted Confirmation Tokens:**
- English: `"yes"`, `"ok"`, `"okay"`, `"confirm"` (case-insensitive)
- Hebrew: `"כן"`, `"אוקיי"`, `"אישור"` (exact match required)

**Negative Override Rule:**
- If a message contains both a positive confirmation token and a negation (`"not"`, `"לא"`), treat as **NOT confirmed**
- Example: `"not ok"`, `"לא אוקיי"` → treated as non-confirmation

**Outside ASK_CONFIRMATION State:**
- The same tokens are treated as normal text, **NOT** confirmation
- Example: User says `"yes"` during ASK_TITLE state → treated as part of title input, not confirmation

**Confirmation State Behavior:**
- If confirmation token detected → proceed to READY state, set `ready=true`
- If non-confirmation input (e.g., "wait", "what?") → transition to `intent="clarify"`, `ready=false`, ask user to confirm or cancel explicitly
- **Confirmation-State Negative Response:** If `"no"` / `"לא"` detected (ONLY in ASK_CONFIRMATION state) → reset flow to INITIAL state, clear `ref` and collected fields safely

**Non-Confirmation vs Explicit Cancel (Critical Distinction):**
- **Non-confirmation** (e.g., "wait", "what?", "change something else"):
  - Do NOT clear collected fields or `ref`
  - Transition to `intent="clarify"`, `ready=false`
  - Ask user explicitly to confirm or cancel
- **Confirmation-State Negative Response** (`"no"` / `"לא"` ONLY in ASK_CONFIRMATION):
  - Reset flow to INITIAL state
  - Clear `ref` and collected fields safely
  - No further questions in this flow
- **Important:** `"no"` / `"לא"` are treated as normal text outside ASK_CONFIRMATION and MUST NOT cancel the flow (e.g., "no deadline" is a valid input, not a cancellation)

### 7. Stable Task Matching Rules

Task identification follows strict priority:

1. **Explicit `task_id`** (strongest match)
   - Explicit task_id means a full identifier string that exactly matches one of the known task IDs present in request.tasks
   - Must be an exact match to a task_id from the tasks list (no partial matches or numeric-only assumptions)

2. **Normalized title match** (exact match required)
   - Lowercase comparison
   - Trimmed whitespace
   - Collapsed internal whitespace (multiple spaces → single space)
   - Exact match required (partial matches are not accepted)

**Multiple Matches:**
- If multiple tasks match the normalized title → emit `command.intent = "clarify"`
- List up to 5 matching tasks (title + id for each)
- Ask user to specify which task
- Include explicit SELECT_TASK state marker (`[[STATE:DELETE:SELECT_TASK]]` or `[[STATE:UPDATE:SELECT_TASK]]`)

**System Guarantees:**
- The system **MUST NEVER** auto-select the "first match"
- The system **MUST NEVER** guess or infer task selection from context
- Task selection is restricted to explicit SELECT_TASK state only

### 8. Language Handling

**Language Detection (per message):**
- Hebrew: if message contains any character in range `\u0590`–`\u05FF`
- Otherwise: English

**Reply Generation:**
- All user-facing text is generated in the detected language
- State markers remain in English (language-independent)
- OpenAI NLG preserves the language of the deterministic reply

**Language Consistency:**
- If a conversation starts in Hebrew, all assistant replies remain in Hebrew
- If a conversation starts in English, all assistant replies remain in English
- Language is re-detected per message (user can switch languages mid-conversation)

---

## Phased Implementation Summary

### Phase 0: Baseline Deterministic Wiring

**Goal:** Establish deterministic routing as the single source of truth, remove intent-rewriting hacks, and audit end-to-end behavior.

**Core Changes:**

1. **`chatbot-service/app/service.py` — `generate_response()`:**
   - Always call deterministic FSM router first
   - Check for active flow priority (if valid state marker exists, continue flow)
   - OpenAI NLG (if enabled) rewrites reply text only after deterministic routing
   - Never use LLM for intent detection, command structure, or readiness decisions

2. **`chatbot-service/app/service.py` — NLG Rewrite Function:**
   - Add `async def _rewrite_reply_nlg(deterministic_reply: str, is_hebrew: bool) -> str`
   - Preserves state markers exactly (never removes or modifies them)
   - Preserves meaning, structure, and language
   - Returns original reply if OpenAI fails

3. **`core-api/app/chat/service.py` — Remove Intent Rewriting:**
   - Remove `update_task_cancelled` and `delete_task_cancelled` logic
   - Set `response.intent = command.intent` if command exists (else keep existing intent)
   - Execution logic depends solely on `command.ready`, not intent name

**State Marker Visibility & Client Impact (Phase 0 Analysis):**

**Mandatory Audit Step:**
- Verify whether the current client (`packages/client/src/components/ChatWidget.tsx`) renders state markers (`[[STATE:...]]`) to users
- Test end-to-end:
  - Send a chat request that triggers a CRUD flow
  - Inspect the reply text in the UI
  - Determine if state markers are visible to users

**Decision Checkpoint:**
- If state markers are visible: document that client-side stripping or hiding mechanism will be required in a later phase
- If state markers are not visible: document that no client changes are needed for marker visibility
- **No client code is modified in Phase 0** (analysis only)

**End-to-End Behavior Audit:**
- Chatbot-service reply format (includes state markers)
- Conversation history persistence (state markers stored in history)
- Client rendering of replies (marker visibility)
- Output: "Client change required later: YES / NO" (decision only, no implementation)

**Invariants:**
- Deterministic routing always produces intent and command before NLG
- OpenAI cannot alter intent, command structure, or readiness
- Core-api executes based on `command.ready` only
- State markers are preserved in conversation history regardless of NLG
- Active flow priority rule prevents intent jumping during multi-step flows

**Validation:**
- Core-api calls chatbot-service without crashing
- Response contains `reply`, `intent`, `command` fields
- No `*_cancelled` intents appear in core-api responses
- State markers are present in conversation history after NLG rewrite

---

### Phase 1: Add Task FSM (Deterministic)

**Goal:** Implement deterministic add_task flow with explicit state markers and strict field order.

**FSM Flow:**
```
INITIAL → ASK_TITLE → ASK_PRIORITY → ASK_DEADLINE → READY
```

**State Definitions:**

1. **INITIAL**
   - **Trigger:** User message contains create/add keywords (English: "create", "add", "new task"; Hebrew: "צור", "הוסף", "משימה חדשה") **AND** no active flow marker exists in conversation_history
   - **Action:** Ask for title, append `[[STATE:CREATE:ASK_TITLE]]` to reply
   - **Command:** `intent="add_task"`, `ready=false`, `missing_fields=["title"]`
   - **Note:** Intent START is triggered by keyword matching only when no active flow exists; FSM step progression is determined by state markers

2. **ASK_TITLE**
   - **State marker:** `[[STATE:CREATE:ASK_TITLE]]`
   - **Trigger:** Last assistant message contains `[[STATE:CREATE:ASK_TITLE]]` (determined by scanning conversation_history from newest to oldest)
   - **Action:** Extract title from current user message, ask for priority, append `[[STATE:CREATE:ASK_PRIORITY]]` to reply
   - **Title extraction:** Non-empty text from user message (trimmed, no validation beyond non-empty)
   - **Command:** `fields.title` populated, `ready=false`, `missing_fields=["priority"]`

3. **ASK_PRIORITY**
   - **State marker:** `[[STATE:CREATE:ASK_PRIORITY]]`
   - **Trigger:** Last assistant message contains `[[STATE:CREATE:ASK_PRIORITY]]`
   - **Action:** Extract priority, validate and map to canonical values, ask for deadline, append `[[STATE:CREATE:ASK_DEADLINE]]` to reply
   - **Priority validation (accepts both English and Hebrew inputs):**
     - **English inputs:** "low", "medium", "high", "urgent" (case-insensitive)
     - **Hebrew inputs:** "נמוכה" → low, "בינונית" → medium, "גבוהה" → high, "דחופה" → urgent
     - **Canonical priority values:** low / medium / high / urgent (stored in `fields.priority`)
   - **Priority mapping (deterministic and rule-based, not LLM-derived):**
     - Hebrew inputs are mapped to canonical English values via fixed mapping
     - Mapping is language-specific but outputs canonical values only
   - **If invalid priority (not in accepted list):** Re-ask priority, stay in ASK_PRIORITY state, keep `[[STATE:CREATE:ASK_PRIORITY]]` marker
   - **Command:** `fields.priority` populated with canonical value (low/medium/high/urgent, normalized to lowercase), `ready=false`, `missing_fields=["deadline"]`

4. **ASK_DEADLINE**
   - **State marker:** `[[STATE:CREATE:ASK_DEADLINE]]`
   - **Trigger:** Last assistant message contains `[[STATE:CREATE:ASK_DEADLINE]]`
   - **Action:** Extract deadline value from current user message
   - **Accepted values:**
     - ISO numeric date: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ` format
     - Explicit none keywords:
       - English: `"no"`, `"none"`, `"skip"`
       - Hebrew: `"לא"`, `"אין"`, `"בלי"`, `"דלג"`
   - **Validation rules:**
     - Format validation only (ISO numeric or explicit none)
     - Relative dates (e.g., "tomorrow", "next week", "יום רביעי") are rejected because they are non-numeric, not because of age
     - If ambiguous or non-numeric (and not explicit none) → re-ask deadline, stay in ASK_DEADLINE state
   - **If valid ISO or explicit none:** Set `ready=true`, transition to READY
   - **Command:** `fields.deadline` (ISO string or null), `ready=true`, `missing_fields=[]`, `confidence=1.0`

5. **READY**
   - **State marker:** None (operation complete)
   - **Trigger:** `ready=true` and core-api execution succeeds
   - **Action:** No further questions in this flow

**Deadline Validation Rules (Format Only):**
- Accept: ISO numeric dates (`YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SSZ`)
- Accept: Explicit none keywords (listed above)
- Reject: Relative dates ("tomorrow", "יום רביעי") because they are non-numeric, not because of age
- Reject: Ambiguous dates (e.g., "next week") because they require context, not because of age
- If rejected: Re-ask for numeric date, stay in ASK_DEADLINE state

**State Inference Logic:**
```
if conversation_history is empty or last message is not assistant:
    return INITIAL

last_assistant_msg = last message with role="assistant" (scanning from newest to oldest)
if "[[STATE:CREATE:ASK_TITLE]]" in last_assistant_msg:
    return ASK_TITLE
if "[[STATE:CREATE:ASK_PRIORITY]]" in last_assistant_msg:
    return ASK_PRIORITY
if "[[STATE:CREATE:ASK_DEADLINE]]" in last_assistant_msg:
    return ASK_DEADLINE

return INITIAL
```

**Command Emission Rules:**
- Always emit `Command` with `intent="add_task"`
- `ready=true` only after deadline step completes (deadline can be null if explicit none)
- `confidence=0.7` if `ready=false`, `1.0` if `ready=true` (deterministic, not LLM-derived)
- `missing_fields` contains next required field (never empty if `ready=false`)

**Core-api Execution Rules:**
- Execute only if: `command.ready == true` AND `command.confidence >= 0.8`
- Require: `fields.title` exists AND `fields.priority` exists
- Allow: `fields.deadline == null` if user said "none" / "אין"
- Never execute if `command.intent == "clarify"`

**Validation Checklist:**
1. "add task" / "תוסיף משימה" → asks for title (same language), includes `[[STATE:CREATE:ASK_TITLE]]`
2. Title provided → asks for priority, includes `[[STATE:CREATE:ASK_PRIORITY]]`
3. Priority provided → asks for deadline, includes `[[STATE:CREATE:ASK_DEADLINE]]`
4. "none" / "אין" → `ready=true`, task created with `deadline=null`
5. Valid ISO date → `ready=true`, task created with `deadline=<date>`
6. Ambiguous date ("tomorrow", "יום רביעי") → re-asks for numeric date, `ready=false`

---

### Phase 2: Delete Task FSM (Deterministic + Confirmation)

**Goal:** Implement deterministic delete_task flow with mandatory confirmation and explicit state markers.

**FSM Flow:**
```
INITIAL → IDENTIFY_TASK → [SELECT_TASK] → ASK_CONFIRMATION → READY
```

**State Definitions:**

1. **INITIAL**
   - **Trigger:** User message contains delete keywords (English: "delete", "remove", "cancel task"; Hebrew: "מחק", "הסר", "בטל משימה") **AND** no active flow marker exists in conversation_history
   - **Action:** Attempt task identification
   - **Note:** Intent START is triggered by keyword matching only when no active flow exists; FSM step progression is determined by state markers

2. **IDENTIFY_TASK**
   - **Task matching priority:**
     1. Explicit `task_id` (full identifier string that exactly matches one of the known task IDs present in request.tasks)
     2. Normalized title match (exact match required)
   - **If task uniquely identified:**
     - Transition to ASK_CONFIRMATION
     - Ask for confirmation, append `[[STATE:DELETE:ASK_CONFIRMATION]]` to reply
     - Confirmation prompt:
       - Hebrew: `"האם אתה בטוח שברצונך למחוק את המשימה '<title>'?"`
       - English: `"Are you sure you want to delete the task '<title>'?"`
     - **Command:** `intent="delete_task"`, `ready=false`, `ref.task_id` or `ref.title` populated, `missing_fields=["confirmation"]`
   - **If multiple tasks match:**
     - Emit `command.intent = "clarify"`
     - `command.ready = false`
     - `command.missing_fields = ["task_selection"]`
     - Reply lists up to 5 matching tasks (title + id), asks user to specify
     - Append `[[STATE:DELETE:SELECT_TASK]]` to reply (explicit state marker for deterministic continuation)
     - Transition to SELECT_TASK state
   - **If no match:**
     - Emit `command.intent = "clarify"`
     - `command.ready = false`
     - `command.missing_fields = ["task_selection"]`
     - Ask user to specify which task
     - No state marker (initial clarify does not advance a flow)

3. **SELECT_TASK** (Clarify Selection State)
   - **State marker:** `[[STATE:DELETE:SELECT_TASK]]`
   - **Trigger:** Last assistant message contains `[[STATE:DELETE:SELECT_TASK]]`
   - **Action:** Interpret user input as task selection
   - **Selection input interpretation:**
     1. **Number 1–5:** Maps to listed option by position (first option = 1, second = 2, etc.)
     2. **Exact task_id match:** Matches explicit task ID if it appears in the displayed options list
     3. **Exact normalized title match:** Matches normalized title if it appears in the displayed options list
   - **Validation:**
     - If input matches one of the selection methods above → task is identified, transition to ASK_CONFIRMATION
     - If input does not match any selection method → re-ask selection, stay in SELECT_TASK state, keep `[[STATE:DELETE:SELECT_TASK]]` marker
   - **If valid selection:**
     - Transition to ASK_CONFIRMATION
     - Ask for confirmation, append `[[STATE:DELETE:ASK_CONFIRMATION]]` to reply
     - Set `command.intent = "delete_task"`, populate `ref` with selected task
   - **Command:** `intent="clarify"` while in SELECT_TASK, `intent="delete_task"` after selection resolved

4. **ASK_CONFIRMATION**
   - **State marker:** `[[STATE:DELETE:ASK_CONFIRMATION]]`
   - **Trigger:** Last assistant message contains `[[STATE:DELETE:ASK_CONFIRMATION]]`
   - **Confirmation detection:**
     - Accepted tokens: Hebrew ("כן", "אוקיי", "אישור"), English ("yes", "ok", "okay", "confirm")
     - Case-insensitive matching for English
     - Negative override: If message contains both positive token and negation ("not", "לא") → treat as NOT confirmed
   - **If confirmation token detected:**
     - Proceed to READY state
     - Set `ready=true`
   - **If non-confirmation input** (e.g., "wait", "what?", "change something else"):
     - Do NOT clear `ref` or collected fields
     - Transition to `intent="clarify"`, `ready=false`
     - Ask user explicitly to confirm or cancel
   - **If confirmation-state negative response** (`"no"` / `"לא"` detected in ASK_CONFIRMATION only):
     - Reset flow to INITIAL state
     - Clear `ref` and collected fields safely
     - No further questions in this flow
   - **Command:** `ready=true` if confirmed, `ready=false` if cancelled or non-confirmation, `confidence=1.0` if `ready=true`, `0.7` if `ready=false`

5. **READY**
   - **Trigger:** `ready=true` and core-api execution succeeds
   - **Action:** No further questions in this flow

**Selection Input Rules (SELECT_TASK State):**
- User selection may be:
  1. A number (1–5) → maps to listed option by position
  2. An exact task_id match among displayed options (must be full identifier string from request.tasks)
  3. An exact normalized title match among displayed options
- No other selection method is allowed
- The system must never guess or auto-select

**Core-api Execution Rules:**
- Execute only if: `command.intent == "delete_task"` AND `command.ready == true` AND `command.ref` exists
- Never execute if `command.intent == "clarify"`

**Validation Checklist:**
1. "delete <title>" → if uniquely matched → asks confirmation with `[[STATE:DELETE:ASK_CONFIRMATION]]`
2. "delete <title>" → if multiple matches → lists options with `[[STATE:DELETE:SELECT_TASK]]` marker
3. "2" (or task_id or exact title) → if in SELECT_TASK → asks confirmation with `[[STATE:DELETE:ASK_CONFIRMATION]]`
4. "yes" / "כן" → `ready=true`, task deleted
5. "not ok" / "לא אוקיי" → `ready=false`, no deletion (negative override)
6. "wait" / "מה?" → `intent="clarify"`, `ready=false`, asks to confirm or cancel (non-confirmation)
7. "no" / "לא" → `ready=false`, flow reset (confirmation-state negative response, only in ASK_CONFIRMATION)

---

### Phase 3: Update Task FSM (Deterministic + Field Selection + Confirmation)

**Goal:** Implement deterministic update_task flow with field selection, value collection, and mandatory confirmation.

**FSM Flow:**
```
INITIAL → IDENTIFY_TASK → [SELECT_TASK] → ASK_FIELD → ASK_VALUE → ASK_CONFIRMATION → READY
```

**State Definitions:**

1. **INITIAL**
   - **Trigger:** User message contains update/change keywords (English: "update", "change", "modify"; Hebrew: "עדכן", "שנה", "ערוך") **AND** no active flow marker exists in conversation_history
   - **Action:** Attempt task identification (same rules as delete)
   - **Note:** Intent START is triggered by keyword matching only when no active flow exists; FSM step progression is determined by state markers

2. **IDENTIFY_TASK**
   - **Task matching:** Same rules as Delete Task FSM
     - Explicit task_id (full identifier string that exactly matches one of the known task IDs present in request.tasks)
     - Normalized title match (exact match required)
   - **If task uniquely identified:**
     - Transition to ASK_FIELD
     - Ask what to change, append `[[STATE:UPDATE:ASK_FIELD]]` to reply
     - Field options:
       - English: "title", "priority", "deadline", "status"
       - Hebrew: "כותרת", "עדיפות", "תאריך יעד", "סטטוס"
     - **Command:** `intent="update_task"`, `ready=false`, `ref.task_id` or `ref.title` populated, `missing_fields=["field_selection"]`
   - **If multiple tasks match:**
     - Emit `command.intent = "clarify"`
     - `command.ready = false`
     - `command.missing_fields = ["task_selection"]`
     - Reply lists up to 5 matching tasks (title + id), asks user to specify
     - Append `[[STATE:UPDATE:SELECT_TASK]]` to reply (explicit state marker for deterministic continuation)
     - Transition to SELECT_TASK state
   - **If no match:**
     - Same clarify handling as Delete Task (no state marker for initial clarify)

3. **SELECT_TASK** (Clarify Selection State)
   - **State marker:** `[[STATE:UPDATE:SELECT_TASK]]`
   - **Trigger:** Last assistant message contains `[[STATE:UPDATE:SELECT_TASK]]`
   - **Action:** Interpret user input as task selection (same rules as Delete Task SELECT_TASK)
   - **Selection input interpretation:**
     1. Number 1–5 → maps to listed option by position
     2. Exact task_id match → matches explicit task ID if it appears in displayed options
     3. Exact normalized title match → matches normalized title if it appears in displayed options
   - **If valid selection:**
     - Transition to ASK_FIELD
     - Ask what to change, append `[[STATE:UPDATE:ASK_FIELD]]` to reply
     - Set `command.intent = "update_task"`, populate `ref` with selected task
   - **Command:** `intent="clarify"` while in SELECT_TASK, `intent="update_task"` after selection resolved

4. **ASK_FIELD**
   - **State marker:** `[[STATE:UPDATE:ASK_FIELD]]`
   - **Trigger:** Last assistant message contains `[[STATE:UPDATE:ASK_FIELD]]`
   - **Action:** Extract field name from current user message
   - **Field validation:**
     - Must be one of: "title", "priority", "deadline", "status"
     - Normalized matching (case-insensitive for English)
   - **If invalid field:** Re-ask field, stay in ASK_FIELD state, keep `[[STATE:UPDATE:ASK_FIELD]]` marker
   - **If valid field:** Transition to ASK_VALUE, ask for new value, append `[[STATE:UPDATE:ASK_VALUE:<FIELD>]]` to reply (e.g., `[[STATE:UPDATE:ASK_VALUE:priority]]`)
   - **Command:** `missing_fields=["<field>_value"]` (field name from user input)

5. **ASK_VALUE**
   - **State marker:** `[[STATE:UPDATE:ASK_VALUE:<FIELD>]]` (e.g., `[[STATE:UPDATE:ASK_VALUE:priority]]`)
   - **Trigger:** Last assistant message contains matching `[[STATE:UPDATE:ASK_VALUE:<FIELD>]]`
   - **Action:** Extract value from current user message
   - **Field-specific validation:**
     - **Priority:** Must be one of ["low", "medium", "high", "urgent"] (case-insensitive)
     - **Deadline:** Same rules as Add Task FSM (ISO numeric or explicit none)
     - **Title:** Any non-empty string (trimmed, no further validation)
     - **Status:** Must map to an existing TaskStatus enum value in core-api via fixed alias map (see Status Alias Mapping below)
   - **Status Alias Mapping (without inventing new enums):**
     - Status inputs are interpreted via a fixed alias map per language, mapping common user words to existing enum values only
     - Example mapping (must use existing TaskStatus enum values from core-api):
       - English: "done" → (existing DONE enum), "open" → (existing OPEN enum), "in progress" → (existing IN_PROGRESS enum)
       - Hebrew: "בוצע" / "סיימתי" → DONE, "פתוח" → OPEN, "בביצוע" → IN_PROGRESS
     - The alias map is language-specific but maps only to existing enum values
     - If input does not map to any existing enum value → re-ask value, stay in ASK_VALUE state
   - **Status Update Safety:**
     - Status updates are restricted to values that already exist in the TaskStatus enum in core-api
     - The system must NOT invent new status values
     - If invalid status (not in alias map) → re-ask value, stay in ASK_VALUE state
   - **If valid value:** Transition to ASK_CONFIRMATION, ask for confirmation, append `[[STATE:UPDATE:ASK_CONFIRMATION]]` to reply
   - **If invalid value:** Re-ask value, stay in ASK_VALUE state, keep same `[[STATE:UPDATE:ASK_VALUE:<FIELD>]]` marker
   - **Command:** `fields.<field>` populated with extracted value (mapped to enum value for status), `missing_fields=["confirmation"]`

6. **ASK_CONFIRMATION**
   - **State marker:** `[[STATE:UPDATE:ASK_CONFIRMATION]]`
   - **Trigger:** Last assistant message contains `[[STATE:UPDATE:ASK_CONFIRMATION]]`
   - **Confirmation detection:** Same rules as Delete Task FSM
     - Accepted tokens: Hebrew ("כן", "אוקיי", "אישור"), English ("yes", "ok", "okay", "confirm")
     - Negative override: If message contains both positive token and negation → treat as NOT confirmed
   - **If confirmation token detected:** Set `ready=true`, transition to READY
   - **If non-confirmation input:** Transition to `intent="clarify"`, `ready=false`, ask to confirm or cancel
   - **If confirmation-state negative response** (`"no"` / `"לא"` detected in ASK_CONFIRMATION only): Reset flow to INITIAL, clear `ref` and collected fields
   - **Command:** `ready=true` if confirmed, `ready=false` if cancelled or non-confirmation, `confidence=1.0` if `ready=true`

7. **READY**
   - **Trigger:** `ready=true` and core-api execution succeeds
   - **Action:** No further questions in this flow

**Command Field Structure:**
- `command.fields` contains **ONLY** updated fields (not all fields)
- Example: If user updates priority only → `fields={priority: "high"}`, `ref.task_id="123"`

**Status Alias Mapping (Critical):**
- Status inputs are interpreted via a fixed alias map per language, mapping common user words to existing TaskStatus enum values only
- The alias map does not invent new enum values; it only maps user input to existing values
- If input does not map to any existing enum value → re-ask, stay in ASK_VALUE state

**Core-api Execution Rules:**
- Execute only if: `command.intent == "update_task"` AND `command.ready == true` AND `command.ref` exists AND `command.fields` is non-empty
- Apply only fields present in `command.fields` (partial updates)
- Never execute if `command.intent == "clarify"`

**Validation Checklist:**
1. "update <title>" → if uniquely matched → asks what to change, includes `[[STATE:UPDATE:ASK_FIELD]]`
2. "update <title>" → if multiple matches → lists options with `[[STATE:UPDATE:SELECT_TASK]]` marker
3. "2" (or task_id or exact title) → if in SELECT_TASK → asks what to change with `[[STATE:UPDATE:ASK_FIELD]]`
4. "priority" → asks for new priority, includes `[[STATE:UPDATE:ASK_VALUE:priority]]`
5. "high" → asks confirmation, includes `[[STATE:UPDATE:ASK_CONFIRMATION]]`
6. "yes" / "כן" → `ready=true`, task updated with `fields.priority="high"`
7. "not ok" → `ready=false`, no update (negative override)
8. "wait" → `intent="clarify"`, asks to confirm or cancel (non-confirmation)
9. Invalid status value → re-asks value, stays in ASK_VALUE state

---

## Invariants and Safety Guarantees

### Invariant 1: Deterministic State Inference

- FSM state is always inferred from the **LAST** state marker found in conversation_history, scanning from newest to oldest (latest marker wins)
- If no marker exists → treat as new request (INITIAL state)
- Earlier markers are ignored (only the most recent marker matters)
- Never infer state from keywords, message content, or free text

### Invariant 2: Active Flow Priority

- If a valid FSM state marker exists in the most recent assistant message, the system **MUST** continue that flow and **MUST NOT** start a new intent via keyword matching, except when the user explicitly cancels
- This ensures deterministic progression through multi-step flows without interruption
- Cancel tokens reset to INITIAL and clear flow context safely

### Invariant 3: Command Structure Consistency

- Every CRUD flow emits a `Command` object
- `command.intent` is always one of: `"add_task"`, `"update_task"`, `"delete_task"`, `"list_tasks"`, `"clarify"`
- `command.ready` is `true` only when:
  - All required fields are collected
  - Confirmation (if required) is received
- `command.confidence` is `0.7` if `ready=false`, `1.0` if `ready=true` (deterministic, not LLM-derived)

### Invariant 4: Core-api Execution Safety

- Core-api executes only when:
  - `command` exists
  - `command.ready == true`
  - `command.confidence >= 0.8`
- Core-api **NEVER** executes when `command.intent == "clarify"`
- Execution logic depends on `command.ready`, not on intent name

### Invariant 5: State Marker Integrity

- State markers are never modified or removed by OpenAI NLG
- State markers are language-independent (always English)
- State markers are stored verbatim in conversation_history

### Invariant 6: Language Consistency

- All user-facing text matches the detected language of the user's message
- State markers remain in English regardless of language
- OpenAI NLG preserves the language of the deterministic reply

### Invariant 7: Confirmation State-Gating

- Confirmation tokens are accepted only when FSM state is `ASK_CONFIRMATION`
- Same tokens outside `ASK_CONFIRMATION` are treated as normal text
- Negative override: messages containing both positive token and negation are treated as NOT confirmed

### Invariant 8: Non-Confirmation vs Cancel Distinction

- **Non-confirmation** (e.g., "wait", "what?") → transition to `intent="clarify"`, preserve collected fields and `ref`
- **Confirmation-State Negative Response** (`"no"` / `"לא"` ONLY in ASK_CONFIRMATION) → reset to INITIAL, clear collected fields and `ref`
- **Global Cancel Commands** (`"cancel"`, `"stop"`, `"never mind"` / `"בטל"`, `"עזוב"`, `"לא משנה"`) → reset to INITIAL from ANY state, clear collected fields and `ref`
- **Important:** `"no"` / `"לא"` outside ASK_CONFIRMATION are treated as normal text and MUST NOT cancel the flow

### Invariant 9: Status Update Safety

- Status updates are restricted to existing TaskStatus enum values in core-api
- Status inputs are mapped via a fixed alias map per language, but only to existing enum values
- The system must never invent new status values
- Invalid status values trigger re-ask, not auto-correction

### Invariant 10: Task Selection Determinism

- Task selection is restricted to explicit SELECT_TASK state only
- Selection input is limited to: number 1–5, exact task_id match, or exact normalized title match
- The system must never guess or auto-select
- SELECT_TASK state ensures deterministic continuation after clarify resolution

---

## File Modification Summary

| File | Phase | Changes |
|------|-------|---------|
| `chatbot-service/app/service.py` | 0 | Change `generate_response()` flow; add `_rewrite_reply_nlg()`; add active flow priority check; remove LLM intent parsing |
| `chatbot-service/app/service.py` | 1 | Rewrite `_handle_potential_create()` with FSM and state markers |
| `chatbot-service/app/service.py` | 2 | Rewrite `_handle_potential_delete()` with FSM, SELECT_TASK state, and confirmation |
| `chatbot-service/app/service.py` | 3 | Rewrite `_handle_potential_update()` with FSM, SELECT_TASK state, field selection, status alias mapping, and confirmation |
| `core-api/app/chat/service.py` | 0 | Remove intent rewriting hacks (`update_task_cancelled`, `delete_task_cancelled`) |
| `core-api/app/chat/service.py` | 1 | Update add_task execution to require `ready=true` |
| `core-api/app/chat/service.py` | 2 | Update delete_task execution to require `ready=true` and confirmation |
| `core-api/app/chat/service.py` | 3 | Update update_task execution to require `ready=true` and confirmation |
| `chatbot-service/app/schemas.py` | 0 | Verify `Command` schema supports all required fields (no changes expected) |
| `core-api/app/chat/schemas.py` | 0 | Verify `ChatResponse` supports `command` field (no changes expected) |

**No other files require modification** (as per hard constraints).

**Client Changes (Future Phase, Not Phase 0):**
- Client changes are determined by Phase 0 audit
- If state markers are visible in UI → client-side stripping/hiding mechanism may be required in a later phase
- Phase 0 only documents the decision; no client code is modified

---

## Summary

This document defines the deterministic FSM-based chat architecture for TaskGenius. All CRUD flows are implemented using explicit state markers, rule-based logic, and strict validation. OpenAI is used strictly for NLG post-processing of reply text, never for intent detection, field extraction, or readiness decisions. Active flow priority ensures deterministic progression through multi-step flows without interruption. Task selection in clarify scenarios uses explicit SELECT_TASK states for deterministic continuation. Status updates use fixed alias mapping to existing enum values only. All invariants and safety guarantees are explicitly enforced at both chatbot-service and core-api levels.

---

**Document Version:** Revision v2.1 (Execution & Priority Patch)  
**Last Updated:** [Current Date]  
**Status:** Implementation Specification
