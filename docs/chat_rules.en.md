# Chat System Rules - Current State Assessment

## Current State Assessment

### What Exists Today

1. **Task Creation Flow (add_task)**:

   - ✅ Title and priority are validated as mandatory before execution
   - ✅ Workflow asks for: title → priority → deadline
   - ✅ Deadline is asked as a step in the flow
   - ✅ Execution only occurs when `ready=true`, `confidence>=0.8`, and both title and priority are present
   - ✅ JSON cleaning logic exists to prevent JSON from appearing in chat UI

2. **Intent Detection**:

   - ✅ System can detect: list_tasks, task_insights, potential_create, potential_update, potential_delete
   - ✅ Rule-based fallback exists when LLM is unavailable
   - ✅ LLM integration with structured output (REPLY + COMMAND format)

3. **Data Flow**:

   - ✅ Current tasks are fetched from database and sent to chatbot-service on every request
   - ✅ Conversation history is sent from frontend to backend
   - ✅ Prompt instructions exist to prefer current tasks data over history

4. **Update/Delete Intent Handling**:
   - ✅ System can detect update/delete intents
   - ✅ System asks for clarification (which task, which field)
   - ⚠️ System asks "Are you ready?" but no explicit confirmation blocking

### What Does NOT Exist Today

1. **Update/Delete Execution**:

   - ❌ No execution logic for `update_task` or `delete_task` in `core-api/app/chat/service.py`
   - ❌ Only `add_task` is executed via chat
   - ❌ Update/delete operations are handled only through direct API endpoints, not via chat

2. **Chat History Clearing**:

   - ❌ Chat history is NOT cleared after CRUD operations
   - ❌ `localStorage` persists history after task mutations
   - ❌ `messages` state in ChatWidget is NOT reset after CRUD
   - ❌ Only manual "Clear" button clears history

3. **Date Validation**:

   - ❌ No validation that enforces date must be numeric or explicit "none" before execution
   - ❌ System tries to parse date, and if it fails, sets to `None` without re-asking
   - ❌ No guarantee that date question is the absolute last step before execution

4. **Confirmation Flows**:

   - ❌ No explicit confirmation step that blocks execution for updates
   - ❌ No explicit confirmation step that blocks execution for deletes
   - ⚠️ System asks "Are you sure?" but doesn't wait for explicit confirmation before proceeding

5. **Field-Specific Update Flow**:
   - ❌ System doesn't explicitly ask "which field do you want to update?" before collecting changes
   - ⚠️ System collects title, priority, deadline but doesn't clarify which specific field is being changed

---

## Blocking Factors (Conceptual/System Blockers)

### Rule 1: Mandatory Fields & Date Understanding

**Status**: ⚠️ Partially Satisfied

**Blocking Factors**:

- Date validation is not enforced: System accepts any deadline value, tries to parse, and if parsing fails, silently sets to `None` without re-asking for numeric format
- For updates: System doesn't explicitly ask "which field do you want to update?" - it assumes all fields (title, priority, deadline) need to be collected
- No validation guard that prevents execution if date is ambiguous (e.g., "יום רביעי" without context)

### Rule 2: Date as Last Step

**Status**: ⚠️ Partially Satisfied

**Blocking Factors**:

- The workflow asks for deadline, but there's no guarantee it's the absolute last step
- The `ready` flag can be set to `true` even if deadline wasn't explicitly asked about in the current conversation (if `has_deadline_asked` is true from history)
- No explicit guard that prevents execution until date question is answered

### Rule 3: Date Clarity Requirement

**Status**: ❌ Not Satisfied

**Blocking Factors**:

- No validation logic that checks if date is numeric or explicit "none" before execution
- Prompt instructions exist but are not enforced by code
- System can proceed with `deadline=None` even if user provided ambiguous date text
- No re-asking mechanism if date parsing fails

### Rule 4: Chat History Clearing After CRUD

**Status**: ❌ Not Satisfied

**Blocking Factors**:

- No automatic clearing of `messages` state in ChatWidget after CRUD
- No automatic clearing of `localStorage` after CRUD
- History persists across CRUD operations
- Only manual "Clear" button clears history
- `taskMutated` event triggers refresh but doesn't clear chat history

### Rule 5: Empty History = Rely Only on Tasks Data

**Status**: ⚠️ Partially Satisfied

**Blocking Factors**:

- History is always sent (even if empty array) - system never operates in truly "empty history" state after CRUD
- Prompt instructs to prefer tasks_data, but history is still present and could influence decisions
- No mechanism to clear history from localStorage after CRUD, so history is never truly empty
- System doesn't distinguish between "new session" (empty history) and "after CRUD" (should be empty but isn't)

### Rule 6: No JSON in Chat UI

**Status**: ✅ Satisfied

**Blocking Factors**:

- None - JSON cleaning logic exists and works

### Rule 7: Intent Understanding for LIST/GET

**Status**: ⚠️ Partially Satisfied

**Blocking Factors**:

- System can detect list_tasks intent
- System receives tasks_data with all fields (priority, status, deadline)
- Prompt instructs to filter by fields, but no explicit validation that all fields are considered
- No explicit test that confirms filtering works for all task fields

### Rule 8: Update Confirmation

**Status**: ❌ Not Satisfied

**Blocking Factors**:

- Update execution doesn't exist in chat flow (only add_task is executed)
- Even if it existed, there's no explicit confirmation step that blocks execution
- System asks "Are you ready?" but doesn't wait for explicit "yes/confirm" before proceeding
- No confirmation intent/state that prevents execution until confirmed

### Rule 9: Delete Confirmation

**Status**: ❌ Not Satisfied

**Blocking Factors**:

- Delete execution doesn't exist in chat flow
- Even if it existed, there's no explicit confirmation step that blocks execution
- System asks "Are you sure?" but doesn't wait for explicit "yes/confirm" before proceeding
- No confirmation intent/state that prevents execution until confirmed
- System doesn't present task description clearly before asking for confirmation

---

## Detailed Rule Analysis

### Rule 1: Task name AND task priority fields are mandatory

**Status**: ⚠️ Partially Satisfied

**What Works**:

- Title and priority are validated before `add_task` execution (line 129 in `core-api/app/chat/service.py`)
- Validation enforces both fields must be present
- System asks for both fields in sequence

**What Blocks Full Satisfaction**:

- Date field: No validation that date must be either "none" (explicit) or numeric before execution
- For updates: System doesn't explicitly ask "which field is being changed?" - it collects all fields
- No validation that prevents execution if date is ambiguous

### Rule 2: Date must be asked as LAST step before CRUD

**Status**: ⚠️ Partially Satisfied

**What Works**:

- Workflow order: title → priority → deadline
- Deadline is asked in the flow

**What Blocks Full Satisfaction**:

- No guarantee that deadline question is the absolute last step
- `ready` flag can be set to `true` even if deadline wasn't explicitly asked in current turn (if asked in history)
- No explicit guard that prevents execution until date question is answered

### Rule 3: If date unclear, ask for numeric format

**Status**: ❌ Not Satisfied

**What Works**:

- Prompt instructions exist to ask for numeric format if unclear
- Prompt warns against using old dates

**What Blocks Satisfaction**:

- No code validation that enforces this rule
- System tries to parse date, and if it fails, sets to `None` without re-asking
- No mechanism to detect "unclear date" and block execution until clarified

### Rule 4: Chat history cleared after CRUD

**Status**: ❌ Not Satisfied

**What Works**:

- Manual "Clear" button exists
- `taskMutated` event is dispatched after CRUD

**What Blocks Satisfaction**:

- No automatic clearing of `messages` state after CRUD
- No automatic clearing of `localStorage` after CRUD
- History persists across CRUD operations
- System doesn't reset to "empty history" state after mutations

### Rule 5: Empty history = rely only on tasks data

**Status**: ⚠️ Partially Satisfied

**What Works**:

- Current tasks are always fetched from database
- Prompt instructs to prefer tasks_data over history

**What Blocks Full Satisfaction**:

- History is never truly empty after CRUD (not cleared)
- History is always sent (even if empty array), so system never operates in "truly empty" state
- No distinction between "new session" and "after CRUD" states

### Rule 6: Never send JSON in chat UI

**Status**: ✅ Satisfied

**What Works**:

- JSON cleaning logic exists (`_parse_llm_response` lines 916-932)
- Regex patterns remove JSON from replies
- Fallback cleaning if JSON leaks into reply

**Blocking Factors**: None

### Rule 7: Correct intent understanding for LIST/GET

**Status**: ⚠️ Partially Satisfied

**What Works**:

- System can detect `list_tasks` intent
- Tasks data includes all fields (priority, status, deadline, etc.)
- Prompt instructs to filter by fields

**What Blocks Full Satisfaction**:

- No explicit validation that all task fields are considered in filtering
- No test that confirms filtering works correctly for all fields
- Intent detection may not always correctly classify LIST vs other intents

### Rule 8: Update confirmation

**Status**: ❌ Not Satisfied

**What Works**:

- System can detect update intent
- System asks for task identification and fields

**What Blocks Satisfaction**:

- Update execution doesn't exist in chat flow (only `add_task` is executed)
- No explicit confirmation step ("Confirm update?") that blocks execution
- System asks "Are you ready?" but doesn't require explicit "yes/confirm" response
- No confirmation state/intent that prevents execution until confirmed

### Rule 9: Delete confirmation

**Status**: ❌ Not Satisfied

**What Works**:

- System can detect delete intent
- System asks "Are you sure?" in some cases

**What Blocks Satisfaction**:

- Delete execution doesn't exist in chat flow
- No explicit confirmation step that blocks execution
- System doesn't always present task description clearly before asking for confirmation
- No confirmation state/intent that prevents execution until confirmed

---

## Rules (Verbatim)

### Rule 1: Mandatory Fields

Task name AND task priority fields are mandatory.

- Date field is mandatory to be understood as either:
  - none (user explicitly does not want a date), OR
  - a numeric date.
- No CRUD action (add / update / change) is allowed unless:
  - task name AND priority are both present.
- For updates, the system must understand exactly WHICH field is being changed.
- No CRUD is allowed without meeting all of the above.

### Rule 2: Date as Last Step

The LAST step before ANY CRUD action (add / update / delete) MUST be asking about the date.

### Rule 3: Date Clarity

If the system does NOT understand whether the user wants a date, OR the date itself is unclear (e.g. free text instead of numbers), it MUST explicitly ask for the date in numeric form. Understanding the date (or explicit none) is mandatory.

### Rule 4: History Clearing After CRUD

After ANY CRUD action (add / update / delete), the chat history MUST be immediately cleared via a page refresh.

### Rule 5: Empty History Behavior

When chat history is empty:

- The system MUST rely ONLY on the current tasks set.
- This MUST happen after EVERY server-side CRUD action: POST / PATCH / PUT / DELETE.
- Chat history MUST also be cleared from localStorage.
- This reset flow is mandatory and occurs EVERY time.
- This behavior is equivalent to logging out and starting a new session.

### Rule 6: No JSON in UI

The chatbot MUST NEVER send JSON responses in the chat UI.

- Only human-readable text responses are allowed.

### Rule 7: Intent Understanding

The chatbot MUST correctly understand INTENT and adapt behavior accordingly.

- For LIST / GET-style intents only:
  - It MUST classify and filter tasks by ALL task fields (priority, status, date, etc.).
- This rule applies ONLY to non-CRUD intents.

### Rule 8: Update Confirmation

When the system understands that the user wants to update an existing task:
a) It MUST ask which field the user wants to update.
b) After collecting the change, the FINAL step before executing the update MUST be: an explicit confirmation request (e.g. "Confirm update?").
c) Only after confirmation may the update be executed.

### Rule 9: Delete Confirmation

Before deleting a task:
a) The system MUST present the task description clearly.
b) The FINAL step before deletion MUST be: an explicit confirmation request (e.g. "Confirm deletion?").
c) Deletion MUST NOT occur without confirmation.

### IMPORTANT GLOBAL FLOW RULE

ANY action that is NOT a GET/LIST action MUST follow a strict flow:
clarification → date resolution → confirmation → execution → IMMEDIATE chat history reset + localStorage cleanup.

- After reset, the system starts from a clean state and relies only on the current tasks payload.
