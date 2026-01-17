# Chatbot Service Upgrade Plan - Final Integrated Plan

## Goal
Upgrade the existing chatbot-service (Python/FastAPI) gradually, with emphasis on **safety**, **quality**, and **good user experience**.

---

## Phase 0: Infrastructure & Testing Setup (Optional Pre-Step)
**Goal:** Prepare infrastructure for testing and future upgrades (optional, can be skipped).

### Tasks:
- [ ] Add improved logging
- [ ] Add better error handling
- [ ] Add validation for requests
- [ ] Prepare expanded test suite

### Tests:
- [ ] All existing tests pass
- [ ] Health check works
- [ ] Error handling works correctly
- [ ] Logging produces clear logs

### Definition of Done:
✅ Infrastructure is ready for future upgrades, all tests pass.

**Note:** This phase is optional - can be skipped and start directly from Phase 1.

---

## Phase 1: LLM Integration (Read-only, Drop-in Replacement)
**Goal:** Replace rule-based logic with LLM (OpenAI), **without changing any API contract**.

### Principles:
- ✅ **Drop-in replacement** - exact same API contract
- ✅ **Read-only** - no actions, no mutations
- ✅ **Fallback** - if LLM fails, fall back to rule-based

### Changes (only in chatbot-service):

#### 1. Configuration (`app/config.py`):
```python
# LLM Configuration
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
USE_LLM: bool = os.getenv("USE_LLM", "false").lower() == "true"
LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "10.0"))
```

#### 2. Service (`app/service.py`):
- Add OpenAI client
- Build prompt that receives:
  - `message` (user message)
  - `tasks` (user's tasks)
  - `weekly_summary` (if exists)
- Generate quality reply
- Fallback: if OpenAI fails → general response

#### 3. Prompt Template:
```
You are a helpful assistant for TaskGenius, a task management system.

User's message: {message}

User's tasks:
{tasks_list}

Weekly summary (if relevant):
{weekly_summary}

Generate a helpful, conversational response. Be concise and friendly.
```

### What doesn't change:
- ❌ No DB access
- ❌ No actions
- ❌ core-api doesn't change at all
- ✅ `/interpret` still returns: `{ "reply": "...", "intent": "...", "suggestions": [...] }`

### Tests:
```python
# Test cases:
- "What are my tasks?" → quality reply based on tasks
- "Show me weekly summary" → reply based on weekly_summary
- "What's urgent for me?" → reply based on priority + urgency
- "What's left this week?" → reply based on upcoming tasks
- LLM fails → fallback to rule-based
```

### Definition of Done:
✅ **Response quality improves significantly**  
✅ **Same flow exactly, no breaking changes**  
✅ **Fallback works if LLM is unavailable**

---

## Phase 2: Intent Quality & Task-Aware Reasoning (Still No Actions)
**Goal:** Make the bot **TaskGenius-aware**, not "general chat".

### Changes:

#### 1. Enhanced Prompt:
- Bot **must** refer to provided tasks
- Ask for clarification when there's ambiguity
- Be aware of context (deadlines, priorities, statuses)
- **Support Hebrew, English, and mixed languages**
- **Understand slang and informal expressions** (e.g., "תוסיף משימה", "מה יש לי היום", "סמן כבוצע")
- **Recognize intent even with informal language**

#### 2. Intent Quality:
`intent` becomes meaningful:
- `list_tasks` - list tasks
- `task_insights` - insights about tasks (deadlines, priorities)
- `potential_create` - intent to create task (but not yet)
- `potential_update` - intent to update task
- `potential_delete` - intent to delete task

#### 3. Clarification Logic:
- If message is ambiguous → ask for clarification
- Suggest relevant options
- Don't assume or guess
- **Collect required fields progressively** (title, priority, deadline, etc.)
- **Only proceed when all required fields are collected**

⚠️ **Still:**
- ❌ No create/delete
- ❌ Only "It seems you want..." or "I need more details..."

### Tests:
```python
# Test cases:
- "add task" → reply: "Which task would you like to add? Give me a title..."
- "delete tomorrow's task" → reply: "You have several tasks tomorrow, which one?"
- "mark X as done" → reply: "I understand you want to mark a task, but..."
- "What's urgent for me this week?" → reply based on high-priority + upcoming tasks
```

### Definition of Done:
✅ **Bot understands deep intent**  
✅ **No dangerous mistakes**  
✅ **Asks for clarification when ambiguous**

---

## Phase 3: Structured Output (Command JSON, Still No Execution)
**Goal:** Add structured output (**without changing external behavior**).

### Internal contract change (Backward Compatible):

#### 1. Schema Update (`app/schemas.py`):
```python
class Command(BaseModel):
    """Structured command from chatbot (optional)."""
    intent: str = Field(description="Command intent: add_task|update_task|delete_task|complete_task|list_tasks|clarify")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    fields: Optional[Dict[str, Any]] = Field(default=None, description="Extracted fields for add_task (title, priority, deadline, etc.)")
    ref: Optional[Dict[str, Any]] = Field(default=None, description="Task reference for update/delete/complete")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter for list_tasks")
    ready: bool = Field(default=False, description="Whether all required fields are collected and command is ready to execute")
    missing_fields: Optional[List[str]] = Field(default=None, description="List of required fields that are still missing")

class ChatResponse(BaseModel):
    """Response from chatbot-service to core-api."""
    reply: str = Field(description="Conversational response to the user")
    intent: Optional[str] = Field(default=None, description="Detected intent (if applicable)")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested actions or follow-ups")
    command: Optional[Command] = Field(default=None, description="Structured command (optional, backward compatible)")
```

#### 2. LLM Prompt Update:
- Add structured output format
- LLM also returns `command` JSON
- **Understand slang and informal language** (Hebrew/English)
- **Extract fields progressively** - collect title, priority, deadline, etc. from conversation
- **Set `ready=true` only when all required fields are present**
- **Set `missing_fields` when information is incomplete**

#### 3. core-api Behavior:
- **core-api ignores `command` at this stage**
- Returns only `reply`, `intent`, `suggestions` (as before)

### Examples:

#### Example 1: Create Task (Clear)
```json
{
  "reply": "I'm ready to create task 'Buy milk'. Would you like to add priority or deadline?",
  "intent": "potential_create",
  "suggestions": ["Add priority", "Set deadline", "Create now"],
  "command": {
    "intent": "add_task",
    "confidence": 0.85,
    "fields": {
      "title": "Buy milk",
      "priority": null,
      "deadline": null
    }
  }
}
```

#### Example 2: Ambiguous Delete
```json
{
  "reply": "You have several tasks tomorrow. Which one would you like to delete?",
  "intent": "potential_delete",
  "suggestions": ["Task A", "Task B", "Cancel"],
  "command": {
    "intent": "delete_task",
    "confidence": 0.3,
    "ref": null
  }
}
```

### Tests:
- [ ] `/interpret` returns valid JSON with `command` (optional)
- [ ] `command` exists only when intent is clear
- [ ] `reply` is still human and clear
- [ ] core-api continues to work without `command`
- [ ] Backward compatibility is maintained

### Definition of Done:
✅ **Separation exists: text for user, JSON for machine**  
✅ **Backward compatible - core-api doesn't need changes**  
✅ **command only when there's sufficient confidence**

---

## Phase 4: Execute Add Task (First Mutation, Controlled)
**Goal:** Enable task creation via chat — **safely**.

### Changes (core-api):

#### 1. ChatService Update (`app/chat/service.py`):
```python
async def process_message(...) -> ChatResponse:
    # ... existing code ...
    
    # Check for add_task command
    if chatbot_response.command and chatbot_response.command.intent == "add_task":
        if chatbot_response.command.confidence >= 0.8:
            # Validate required fields
            if chatbot_response.command.fields and chatbot_response.command.fields.get("title"):
                # Create task via repository
                new_task = await task_repository.create(...)
                # Update reply
                chatbot_response.reply = f"✅ Added task: '{new_task.title}'"
                chatbot_response.intent = "create_task"
            else:
                # Clarify
                chatbot_response.reply = "I need a title for the task. What's the title?"
        else:
            # Low confidence - don't execute
            chatbot_response.reply = "I'm not sure what you mean. Can you clarify?"
    
    return chatbot_response
```

#### 2. Validation:
- ✅ `confidence >= 0.8` - only high confidence
- ✅ `title` required - don't assume
- ✅ Error handling - if creation fails

### chatbot-service:

#### 1. Confidence Calculation:
- High confidence only when title is clear
- Low confidence if details are missing

#### 2. Clarification:
- Instead of guessing → ask for details
- Suggest relevant options

### Tests:
```python
# Test cases:
- "add task buy milk tomorrow" → task created, confidence >= 0.8
- "add task" → clarify, no creation, confidence < 0.8
- "add task with priority high" → clarify (missing title), confidence < 0.8
- Validation error → clear error message to user
```

### Definition of Done:
✅ **Add works safely**  
✅ **No incorrect creations**  
✅ **Clarification when ambiguous**

---

## Phase 5: Update / Complete / Delete with Resolver
**Goal:** Enable update/delete **without errors**.

### core-api: Resolver Layer

#### 1. Task Resolver (`app/chat/resolver.py`):
```python
async def resolve_task_reference(
    command: Command,
    task_repository: TaskRepositoryInterface,
    user_id: str
) -> Tuple[Optional[Task], List[Task]]:
    """
    Resolve task reference from command.
    
    Returns:
        (task, candidates) - task if unambiguous, candidates if ambiguous
    """
    if command.ref and command.ref.get("task_id"):
        # Direct task ID
        task = await task_repository.get_by_id(command.ref["task_id"], user_id)
        return (task, [])
    
    # Query-based resolution
    if command.filter:
        candidates = await task_repository.filter_by(query, user_id)
        if len(candidates) == 1:
            return (candidates[0], [])
        elif len(candidates) > 1:
            return (None, candidates[:3])  # Top 3
    
    return (None, [])
```

#### 2. ChatService Integration:
```python
async def process_message(...) -> ChatResponse:
    # ... existing code ...
    
    if chatbot_response.command:
        intent = chatbot_response.command.intent
        
        if intent in ["update_task", "delete_task", "complete_task"]:
            task, candidates = await resolve_task_reference(...)
            
            if task:
                # Unambiguous - execute
                if intent == "delete_task":
                    await task_repository.delete(task.id, user_id)
                    chatbot_response.reply = f"✅ Deleted task: '{task.title}'"
                # ... update/complete ...
            elif candidates:
                # Ambiguous - clarify
                chatbot_response.reply = "Which task? " + format_candidates(candidates)
                chatbot_response.command.confidence = 0.0  # Don't execute
            else:
                # Not found
                chatbot_response.reply = "I couldn't find such a task. Can you clarify?"
```

### chatbot-service:

#### 1. Doesn't execute:
- chatbot-service only interprets
- Returns `command` with `ref` or `filter`
- Doesn't call DB directly

#### 2. Reference Extraction:
- If task ID in message → `ref.task_id`
- If query → `filter` (title, deadline, etc.)

### Tests:
```python
# Test cases:
- "mark buy milk as done" (unambiguous) → task 1 → execute
- "delete tomorrow's task" (ambiguous) → 3 candidates → clarify
- "delete task abc123" (task_id) → execute
- "delete non-existent task" → not found → error message
- No deletion without clear selection
```

### Definition of Done:
✅ **No destructive actions without clarity**  
✅ **Resolver works - distinguishes between unambiguous and ambiguous**  
✅ **Clarification when ambiguous**

---

## Recommended Execution Order:

```
Phase 0: Infrastructure (Optional)
   ↓
Phase 1: LLM Integration (Read-only)
   ↓ (tests - response quality improves)
Phase 2: Intent Quality & Task-Aware Reasoning
   ↓ (tests - bot understands deep intents)
Phase 3: Structured Output (Command JSON)
   ↓ (tests - valid JSON, backward compatible)
Phase 4: Execute Add Task
   ↓ (tests - Add works, no errors)
Phase 5: Update / Complete / Delete with Resolver
   ↓ (tests - Resolver works, no mistakes)
✅ Complete
```

---

## Working Principles:

1. **Work in phases**: Each phase starts only after the previous phase passes all tests.
2. **Tests in each phase**: Before moving to the next phase, all tests of the current phase must pass.
3. **Backward Compatibility**: Until Phase 3, core-api doesn't change at all.
4. **Safety First**: Only high confidence → execution. Ambiguity → clarification.
5. **No DB Access**: chatbot-service doesn't touch DB, only interprets.

---

## Important Notes:

- **Phase 1-2**: Read-only only, no mutations
- **Phase 3**: Preparation for mutations, but still doesn't execute
- **Phase 4**: First mutation (Add) - safest
- **Phase 5**: More dangerous mutations (Delete/Update) - only with resolver
- **Fallback**: Each phase needs fallback if something fails

---

## Quality Criteria:

✅ **Safety**: No actions without high confidence or without clarification  
✅ **Quality**: Quality and relevant responses  
✅ **User Experience**: Clear and responsive to user  
✅ **Reliability**: Fallback and error handling at every stage
