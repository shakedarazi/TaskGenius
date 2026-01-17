# תוכנית שדרוג Chatbot Service - תוכנית סופית משולבת

## מטרה
לשדרג את ה-chatbot-service הקיים (Python/FastAPI) בהדרגה, עם דגש על **בטיחות**, **איכות**, ו**חווית משתמש טובה**.

---

## Phase 0: Infrastructure & Testing Setup (Optional Pre-Step)
**מטרה:** הכנת תשתית לבדיקות ושדרוגים עתידיים (optional, ניתן לדלג).

### משימות:
- [ ] הוספת logging משופר
- [ ] הוספת error handling טוב יותר
- [ ] הוספת validation ל-requests
- [ ] הכנת test suite מורחב

### בדיקות:
- [ ] כל ה-tests הקיימים עוברים
- [ ] Health check עובד
- [ ] Error handling עובד כראוי
- [ ] Logging מייצר logs ברורים

### Definition of Done:
✅ התשתית מוכנה לשדרוגים עתידיים, כל ה-tests עוברים.

**הערה:** שלב זה אופציונלי - אפשר לדלג עליו ולהתחיל ישר מ-Phase 1.

---

## Phase 1: LLM Integration (Read-only, Drop-in Replacement)
**מטרה:** להחליף את ה-rule-based logic ב-LLM (OpenAI), **בלי לשנות שום חוזה API**.

### עקרונות:
- ✅ **Drop-in replacement** - אותו API contract בדיוק
- ✅ **Read-only** - אין actions, אין mutations
- ✅ **Fallback** - אם LLM נופל, חוזרים ל-rule-based

### שינויים (רק ב-chatbot-service):

#### 1. Configuration (`app/config.py`):
```python
# LLM Configuration
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
USE_LLM: bool = os.getenv("USE_LLM", "false").lower() == "true"
LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "10.0"))
```

#### 2. Service (`app/service.py`):
- הוספת OpenAI client
- בניית prompt שמקבל:
  - `message` (user message)
  - `tasks` (user's tasks)
  - `weekly_summary` (אם קיים)
- ייצור reply איכותי
- Fallback: אם OpenAI נופל → תשובה כללית

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

### מה לא משתנה:
- ❌ אין DB access
- ❌ אין actions
- ❌ core-api לא משתנה בכלל
- ✅ `/interpret` עדיין מחזיר: `{ "reply": "...", "intent": "...", "suggestions": [...] }`

### בדיקות:
```python
# Test cases:
- "מה המשימות שלי?" → reply איכותי על בסיס tasks
- "תראה לי סיכום שבועי" → reply על בסיס weekly_summary
- "מה דחוף לי?" → reply מבוסס priority + urgency
- "מה נשאר השבוע?" → reply מבוסס upcoming tasks
- LLM נופל → fallback ל-rule-based
```

### Definition of Done:
✅ **איכות תשובות עולה משמעותית**  
✅ **אותו flow בדיוק, בלי שבירה**  
✅ **Fallback עובד אם LLM לא זמין**

---

## Phase 2: Intent Quality & Task-Aware Reasoning (Still No Actions)
**מטרה:** להפוך את הבוט ל-**TaskGenius-aware**, לא "צ'אט כללי".

### שינויים:

#### 1. Prompt משודרג:
- הבוט **חייב** להתייחס ל-tasks שסופקו
- לבקש הבהרה כשיש עמימות
- להיות מודע ל-context (deadlines, priorities, statuses)

#### 2. Intent Quality:
`intent` הופך להיות משמעותי:
- `list_tasks` - רשימת משימות
- `task_insights` - תובנות על tasks (deadlines, priorities)
- `potential_create` - כוונה ליצור משימה (אבל עדיין לא)
- `potential_update` - כוונה לעדכן משימה
- `potential_delete` - כוונה למחוק משימה

#### 3. Clarification Logic:
- אם הודעה עמומה → מבקש הבהרה
- מציע options רלוונטיים
- לא מניח או מנחש

⚠️ **עדיין:**
- ❌ אין יצירה/מחיקה
- ❌ רק "נראה שאתה רוצה..." או "אני צריך עוד פרטים..."

### בדיקות:
```python
# Test cases:
- "תוסיף משימה" → reply: "איזה משימה תרצה להוסיף? תן לי title..."
- "תמחק את המשימה של מחר" → reply: "יש לך כמה משימות מחר, איזו?"
- "סמן את X כבוצע" → reply: "אני מבין שאתה רוצה לסמן משימה, אבל..."
- "מה דחוף לי השבוע?" → reply מבוסס high-priority + upcoming tasks
```

### Definition of Done:
✅ **הבוט מבין כוונה עמוקה**  
✅ **לא עושה טעויות מסוכנות**  
✅ **מבקש הבהרה כשיש עמימות**

---

## Phase 3: Structured Output (Command JSON, Still No Execution)
**מטרה:** להוסיף פלט מובנה (**בלי לשנות התנהגות חיצונית**).

### שינוי חוזה פנימי (Backward Compatible):

#### 1. Schema Update (`app/schemas.py`):
```python
class Command(BaseModel):
    """Structured command from chatbot (optional)."""
    intent: str = Field(description="Command intent: add_task|update_task|delete_task|complete_task|list_tasks|clarify")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    fields: Optional[Dict[str, Any]] = Field(default=None, description="Extracted fields for add_task")
    ref: Optional[Dict[str, Any]] = Field(default=None, description="Task reference for update/delete/complete")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter for list_tasks")

class ChatResponse(BaseModel):
    """Response from chatbot-service to core-api."""
    reply: str = Field(description="Conversational response to the user")
    intent: Optional[str] = Field(default=None, description="Detected intent (if applicable)")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested actions or follow-ups")
    command: Optional[Command] = Field(default=None, description="Structured command (optional, backward compatible)")
```

#### 2. LLM Prompt Update:
- הוספת structured output format
- LLM מחזיר גם `command` JSON

#### 3. core-api Behavior:
- **core-api מתעלם מ-`command` בשלב זה**
- מחזיר רק `reply`, `intent`, `suggestions` (כמו קודם)

### דוגמאות:

#### Example 1: Create Task (Clear)
```json
{
  "reply": "אני מוכן ליצור משימה 'לקנות חלב'. תרצה להוסיף priority או deadline?",
  "intent": "potential_create",
  "suggestions": ["Add priority", "Set deadline", "Create now"],
  "command": {
    "intent": "add_task",
    "confidence": 0.85,
    "fields": {
      "title": "לקנות חלב",
      "priority": null,
      "deadline": null
    }
  }
}
```

#### Example 2: Ambiguous Delete
```json
{
  "reply": "יש לך כמה משימות מחר. איזו תרצה למחוק?",
  "intent": "potential_delete",
  "suggestions": ["Task A", "Task B", "Cancel"],
  "command": {
    "intent": "delete_task",
    "confidence": 0.3,
    "ref": null
  }
}
```

### בדיקות:
- [ ] `/interpret` מחזיר JSON תקין עם `command` (optional)
- [ ] `command` קיים רק כשיש כוונה ברורה
- [ ] `reply` עדיין אנושי וברור
- [ ] core-api ממשיך לעבוד גם בלי `command`
- [ ] Backward compatibility נשמרת

### Definition of Done:
✅ **יש הפרדה: טקסט למשתמש, JSON למכונה**  
✅ **Backward compatible - core-api לא צריך שינויים**  
✅ **command רק כשיש confidence מספק**

---

## Phase 4: Execute Add Task (Mutation ראשונה, מבוקרת)
**מטרה:** לאפשר יצירת משימה דרך צ'אט — **בצורה בטוחה**.

### שינויים (core-api):

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
                chatbot_response.reply = f"✅ הוספתי משימה: '{new_task.title}'"
                chatbot_response.intent = "create_task"
            else:
                # Clarify
                chatbot_response.reply = "אני צריך title למשימה. מה התואר?"
        else:
            # Low confidence - don't execute
            chatbot_response.reply = "אני לא בטוח למה אתה מתכוון. תוכל לחדד?"
    
    return chatbot_response
```

#### 2. Validation:
- ✅ `confidence >= 0.8` - רק confidence גבוה
- ✅ `title` חובה - לא מניח
- ✅ Error handling - אם יצירה נכשלת

### chatbot-service:

#### 1. Confidence Calculation:
- confidence גבוה רק כשיש title ברור
- confidence נמוך אם חסרים פרטים

#### 2. Clarification:
- במקום לנחש → מבקש פרטים
- מציע options רלוונטיים

### בדיקות:
```python
# Test cases:
- "תוסיף משימה לקנות חלב מחר" → task נוצר, confidence >= 0.8
- "תוסיף משימה" → clarify, אין יצירה, confidence < 0.8
- "תוסיף משימה עם priority high" → clarify (חסר title), confidence < 0.8
- Validation error → error message ברור למשתמש
```

### Definition of Done:
✅ **Add עובד בצורה בטוחה**  
✅ **אין יצירות שגויות**  
✅ **Clarification כשיש עמימות**

---

## Phase 5: Update / Complete / Delete with Resolver
**מטרה:** לאפשר עדכון/מחיקה **בלי טעויות**.

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
                    chatbot_response.reply = f"✅ מחקתי משימה: '{task.title}'"
                # ... update/complete ...
            elif candidates:
                # Ambiguous - clarify
                chatbot_response.reply = "איזו משימה? " + format_candidates(candidates)
                chatbot_response.command.confidence = 0.0  # Don't execute
            else:
                # Not found
                chatbot_response.reply = "לא מצאתי משימה כזו. תוכל לחדד?"
```

### chatbot-service:

#### 1. לא מבצע:
- chatbot-service רק מפרש
- מחזיר `command` עם `ref` או `filter`
- לא קורא ל-DB ישירות

#### 2. Reference Extraction:
- אם יש task ID במסר → `ref.task_id`
- אם יש query → `filter` (title, deadline, etc.)

### בדיקות:
```python
# Test cases:
- "סמן את לקנות חלב כבוצע" (חד-משמעי) → task 1 → execute
- "תמחק את המשימה של מחר" (עמום) → 3 candidates → clarify
- "תמחק task abc123" (task_id) → execute
- "תמחק משימה שלא קיימת" → not found → error message
- אין מחיקה בלי בחירה ברורה
```

### Definition of Done:
✅ **אין destructive actions לא ברורות**  
✅ **Resolver עובד - מבחין בין חד-משמעי לעמום**  
✅ **Clarification כשיש עמימות**

---

## סדר ביצוע מומלץ:

```
Phase 0: Infrastructure (Optional)
   ↓
Phase 1: LLM Integration (Read-only)
   ↓ (בדיקות - איכות תשובות עולה)
Phase 2: Intent Quality & Task-Aware Reasoning
   ↓ (בדיקות - הבוט מבין כוונות עמוקות)
Phase 3: Structured Output (Command JSON)
   ↓ (בדיקות - JSON תקין, backward compatible)
Phase 4: Execute Add Task
   ↓ (בדיקות - Add עובד, אין שגיאות)
Phase 5: Update / Complete / Delete with Resolver
   ↓ (בדיקות - Resolver עובד, אין טעויות)
✅ סיום
```

---

## כללי עבודה:

1. **עבודה בשלבים**: כל phase מתחיל רק אחרי שה-phase הקודם עבר את כל הבדיקות.
2. **בדיקות בכל phase**: לפני מעבר ל-phase הבא, כל הבדיקות של ה-phase הנוכחי צריכות לעבור.
3. **Backward Compatibility**: עד Phase 3, core-api לא משתנה בכלל.
4. **Safety First**: רק confidence גבוה → execution. עמימות → clarification.
5. **No DB Access**: chatbot-service לא נוגע ב-DB, רק מפרש.

---

## הערות חשובות:

- **Phase 1-2**: רק read-only, אין mutations
- **Phase 3**: הכנה ל-mutations, אבל עדיין לא מבצע
- **Phase 4**: Mutation ראשונה (Add) - הכי בטוחה
- **Phase 5**: Mutations מסוכנות יותר (Delete/Update) - רק עם resolver
- **Fallback**: כל שלב צריך fallback אם משהו נופל

---

## קריטריוני איכות:

✅ **Safety**: אין actions ללא confidence גבוה או ללא clarification  
✅ **Quality**: תשובות איכותיות ורלוונטיות  
✅ **User Experience**: ברור ומענה למשתמש  
✅ **Reliability**: Fallback ו-error handling בכל שלב
