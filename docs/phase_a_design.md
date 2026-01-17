# Phase A: Design & Enforcement Plan for Chat System Rules

## Overview

This document defines where and how each rule (1-9 + Global Flow Rule) will be enforced, what minimal new logic/state is required, and whether core-api changes are necessary.

---

## Rule-by-Rule Design

### Rule 1: Mandatory Fields & Date Understanding

**Requirement:**
- Task name AND priority are mandatory
- Date must be understood as either "none" (explicit) OR numeric
- For updates: must understand exactly WHICH field is being changed
- No CRUD without meeting all above

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - Add date validation function: `_validate_deadline_format(deadline: str | None) -> bool`
   - Modify `_parse_llm_response` to validate deadline format before setting `ready=true`
   - If deadline is provided but not numeric and not explicit "none", set `ready=false`, add to `missing_fields`
   - For updates: Modify `_handle_potential_update` to explicitly ask "which field?" as first step

2. **core-api** (`app/chat/service.py`):
   - **REQUIRES CORE-API CHANGE** (minimal, additive)
   - Add date validation before execution (lines 149-155)
   - If deadline is provided but invalid format, reject execution and return error response
   - This is a safety guard - should not execute if chatbot-service validation fails

**New Logic Required:**
- Date format validator (ISO date string or explicit "none" keywords)
- Field selection prompt for updates
- Validation guard in execution path

**Core-API Change Required:** ✅ YES (safety guard for date validation)

---

### Rule 2: Date as Last Step

**Requirement:**
- The LAST step before ANY CRUD action MUST be asking about the date

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - Add workflow state tracking: `_get_workflow_state(conversation_history, current_intent) -> str`
   - States: `"collecting_title"`, `"collecting_priority"`, `"collecting_deadline"`, `"ready_for_confirmation"`
   - Modify `_build_prompt` to enforce: deadline question MUST come after title+priority are collected
   - Modify `_parse_llm_response` to check: if `ready=true` but deadline wasn't explicitly asked in last assistant message, set `ready=false`

2. **core-api**: 
   - **Does NOT require core-api change** (workflow is chatbot-service responsibility)

**New Logic Required:**
- Workflow state machine
- Last-step validation before setting `ready=true`

**Core-API Change Required:** ❌ NO

---

### Rule 3: Date Clarity Requirement

**Requirement:**
- If date unclear, MUST ask for numeric format
- Understanding date (or explicit none) is mandatory

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - Add `_validate_and_normalize_deadline(deadline: str | None, conversation_history: List) -> tuple[bool, Optional[str]]`
   - Returns: `(is_valid, normalized_iso_string_or_none)`
   - If deadline is ambiguous text (e.g., "יום רביעי", "tomorrow" without context), return `(False, None)`
   - Modify `_parse_llm_response` to check date clarity
   - If unclear, set `ready=false`, add "deadline" to `missing_fields`, modify reply to ask for numeric format

2. **core-api** (`app/chat/service.py`):
   - **REQUIRES CORE-API CHANGE** (minimal, additive)
   - Add date format validation before execution (lines 149-155)
   - Reject if deadline is not ISO format or explicit null

**New Logic Required:**
- Date ambiguity detector
- Re-asking mechanism for unclear dates
- Validation guard in execution

**Core-API Change Required:** ✅ YES (safety guard for date format)

---

### Rule 4: Chat History Clearing After CRUD

**Requirement:**
- After ANY CRUD action, chat history MUST be immediately cleared

**Enforcement Location:**
1. **Frontend** (`packages/client/src/components/ChatWidget.tsx`):
   - Modify `handleSubmit` (around line 164)
   - After detecting CRUD completion (`response.intent === 'create_task' | 'update_task' | 'delete_task'`):
     - Clear `messages` state: `setMessages([])`
     - Clear `localStorage`: `localStorage.removeItem(CHAT_HISTORY_KEY)`
     - This happens immediately after successful CRUD response

2. **chatbot-service**: 
   - **Does NOT require change** (frontend responsibility)

**New Logic Required:**
- Automatic history clearing in ChatWidget after CRUD detection

**Core-API Change Required:** ❌ NO

---

### Rule 5: Empty History Behavior

**Requirement:**
- When history is empty, rely ONLY on current tasks set
- Must happen after EVERY server-side CRUD
- History must be cleared from localStorage
- Equivalent to logging out and starting new session

**Enforcement Location:**
1. **Frontend** (`packages/client/src/components/ChatWidget.tsx`):
   - Same as Rule 4: Clear history after CRUD
   - Ensure `conversation_history` sent to API is empty array `[]` after CRUD

2. **chatbot-service** (`app/service.py`):
   - Modify `_build_prompt` to detect empty history
   - If `conversation_history` is empty or None, add explicit instruction: "History is empty - rely ONLY on current tasks data"

3. **core-api**: 
   - **Does NOT require core-api change**

**New Logic Required:**
- History clearing (same as Rule 4)
- Empty history detection in prompt building

**Core-API Change Required:** ❌ NO

---

### Rule 6: No JSON in Chat UI

**Requirement:**
- Chatbot MUST NEVER send JSON responses in chat UI

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - **Does NOT require change** (already implemented in `_parse_llm_response`, lines 916-932)
   - Keep existing JSON cleaning logic

**New Logic Required:**
- None (already exists)

**Core-API Change Required:** ❌ NO

---

### Rule 7: Intent Understanding for LIST/GET

**Requirement:**
- Must correctly understand intent
- For LIST/GET: must classify and filter by ALL task fields

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - Modify `_build_prompt` to explicitly list all task fields available for filtering
   - Add instruction: "When filtering tasks, consider ALL fields: priority, status, deadline, title, category"
   - Modify `_handle_task_insights` to ensure all fields are considered

2. **core-api**: 
   - **Does NOT require core-api change**

**New Logic Required:**
- Enhanced prompt instructions for comprehensive field filtering
- Validation that filtering logic considers all fields

**Core-API Change Required:** ❌ NO

---

### Rule 8: Update Confirmation

**Requirement:**
- Must ask which field
- After collecting change, FINAL step must be explicit confirmation
- Only after confirmation may update be executed

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - Modify `_handle_potential_update` to:
     - First ask: "Which field do you want to update? (title/priority/deadline/status)"
     - After field is identified, collect new value
     - After deadline is resolved (Rule 2), ask: "Confirm update? (yes/no)"
     - Only set `ready=true` if confirmation is explicit "yes" or equivalent

2. **core-api** (`app/chat/service.py`):
   - **REQUIRES CORE-API CHANGE** (major, but isolated)
   - Add `update_task` execution logic (similar to `add_task`, lines 127-199)
   - Validate: `command.intent == "update_task"`, `command.confidence >= 0.8`, `command.ready == true`
   - Validate: `command.ref` contains valid `task_id` or `title` for matching
   - Validate: `command.fields` contains at least one field to update
   - Call `task_repository.update(task_id, owner_id, updates_dict)`
   - Return confirmation message

**New Logic Required:**
- Field selection prompt
- Confirmation state tracking
- Update execution in core-api

**Core-API Change Required:** ✅ YES (update_task execution doesn't exist)

---

### Rule 9: Delete Confirmation

**Requirement:**
- Must present task description clearly
- FINAL step must be explicit confirmation
- Deletion MUST NOT occur without confirmation

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - Modify `_handle_potential_delete` to:
     - First identify task (already exists)
     - Present full task description: "Task: [title], Priority: [priority], Deadline: [deadline]"
     - Ask: "Confirm deletion? (yes/no)"
     - Only set `ready=true` if confirmation is explicit "yes"

2. **core-api** (`app/chat/service.py`):
   - **REQUIRES CORE-API CHANGE** (major, but isolated)
   - Add `delete_task` execution logic (similar to `add_task`, lines 127-199)
   - Validate: `command.intent == "delete_task"`, `command.confidence >= 0.8`, `command.ready == true`
   - Validate: `command.ref` contains valid `task_id` or `title` for matching
   - Call `task_repository.delete(task_id, owner_id)`
   - Return confirmation message

**New Logic Required:**
- Task description presentation
- Confirmation state tracking
- Delete execution in core-api

**Core-API Change Required:** ✅ YES (delete_task execution doesn't exist)

---

### Global Flow Rule

**Requirement:**
- Any non-GET action MUST follow: clarification → date resolution → confirmation → execution → hard reset

**Enforcement Location:**
1. **chatbot-service** (`app/service.py`):
   - Implement workflow state machine:
     - `clarification`: Asking for missing info (title, priority, task identification)
     - `date_resolution`: Asking about deadline (Rule 2: must be last step before confirmation)
     - `confirmation`: Asking for explicit confirmation (Rules 8-9)
     - `execution`: Ready to execute (set by core-api after validation)
     - `hard_reset`: History cleared (handled by frontend)
   - Modify `_build_prompt` to enforce flow order
   - Modify `_parse_llm_response` to validate flow state before setting `ready=true`

2. **core-api** (`app/chat/service.py`):
   - **REQUIRES CORE-API CHANGE** (additive, for update/delete)
   - Validate workflow state in command before execution
   - After execution, return response that triggers frontend reset

3. **Frontend** (`packages/client/src/components/ChatWidget.tsx`):
   - After CRUD response, clear history (Rules 4-5)

**New Logic Required:**
- Workflow state machine
- Flow validation
- History reset trigger

**Core-API Change Required:** ✅ YES (for update/delete execution)

---

## Summary: Core-API Changes Required

### Files Requiring Changes:

1. **`services/core-api/app/chat/service.py`**:
   - **Reason**: Rules 1, 3, 8, 9, Global Flow
   - **Functions to modify**:
     - `process_message` (lines 42-208):
       - Add date validation before execution (Rules 1, 3)
       - Add `update_task` execution logic (Rule 8)
       - Add `delete_task` execution logic (Rule 9)
       - Add workflow state validation (Global Flow)
   - **Impact**: Additive only - no existing behavior changed
   - **Risk**: Low - isolated execution paths

### Files NOT Requiring Changes:
- `services/core-api/app/chat/router.py` - No changes needed
- `services/core-api/app/chat/schemas.py` - No changes needed
- `services/core-api/app/tasks/*` - No changes needed (repositories/services already exist)

---

## Implementation Groups

### Group 1: Date Resolution & Validation (Rules 1-3)
**Files:**
- `services/chatbot-service/app/service.py`
- `services/core-api/app/chat/service.py` (date validation only)

**Changes:**
- Date format validator
- Date ambiguity detector
- Last-step validation
- Execution guard for date format

**Core-API Impact:** Minimal (additive validation)

---

### Group 2: Confirmation Flows (Rules 8-9)
**Files:**
- `services/chatbot-service/app/service.py`
- `services/core-api/app/chat/service.py` (update/delete execution)

**Changes:**
- Field selection for updates
- Confirmation state tracking
- Update execution logic
- Delete execution logic
- Task description presentation

**Core-API Impact:** Major (new execution paths, but isolated)

---

### Group 3: History Reset & Session Semantics (Rules 4-5 + Global Flow)
**Files:**
- `packages/client/src/components/ChatWidget.tsx`
- `services/chatbot-service/app/service.py` (workflow state)

**Changes:**
- Automatic history clearing after CRUD
- Empty history detection
- Workflow state machine

**Core-API Impact:** None

---

### Group 4: Intent Guarantees for LIST/GET (Rule 7)
**Files:**
- `services/chatbot-service/app/service.py`

**Changes:**
- Enhanced prompt instructions
- Field filtering validation

**Core-API Impact:** None

---

## Safety Guarantees

1. **No Breaking Changes**:
   - All changes are additive
   - Existing `add_task` flow unchanged
   - Existing API endpoints unchanged

2. **Backward Compatibility**:
   - Old clients continue to work
   - New validation only applies to new execution paths

3. **Isolation**:
   - Update/delete execution is separate from add_task
   - Date validation is separate from existing parsing
   - History clearing is frontend-only

4. **Testability**:
   - Each rule can be tested independently
   - Validation logic is pure functions
   - Execution paths are isolated

---

## Approval Checklist

- [ ] Rule 1: Date validation approach approved
- [ ] Rule 2: Workflow state machine approach approved
- [ ] Rule 3: Date clarity validation approved
- [ ] Rule 4: Frontend history clearing approved
- [ ] Rule 5: Empty history behavior approved
- [ ] Rule 6: No changes needed (already satisfied)
- [ ] Rule 7: Enhanced filtering approved
- [ ] Rule 8: Update confirmation flow approved
- [ ] Rule 9: Delete confirmation flow approved
- [ ] Global Flow: State machine approach approved
- [ ] Core-API changes approved (service.py only)

---

## Next Steps (After Approval)

1. Implement Group 1 (Date Resolution)
2. Implement Group 2 (Confirmation Flows)
3. Implement Group 3 (History Reset)
4. Implement Group 4 (Intent Guarantees)
5. Add tests for each rule
6. Verify no breaking changes
