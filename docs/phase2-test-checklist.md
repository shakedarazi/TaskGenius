# Phase 2: סדרת בחינה (Test Checklist)

## לפני הבדיקה - Restart

### 1. Rebuild chatbot-service
```bash
docker compose up -d --build chatbot-service
```

### 2. בדוק שהשירות עובד
```bash
docker compose ps chatbot-service
docker compose logs chatbot-service --tail 20
```

---

## סדרת בחינה - Phase 2

### ✅ חלק 1: Intent Quality - זיהוי כוונות משופר

#### 1.1 Task Insights (תובנות על משימות)
**בדיקה:** הבוט מזהה שאלות על דחיפות, עדיפויות, תאריכים

**הודעות לבדיקה:**
- [ ] "What's urgent for me?" (אנגלית)
- [ ] "מה דחוף לי?" (עברית)
- [ ] "Show me high priority tasks" (אנגלית)
- [ ] "מה המשימות בעדיפות גבוהה?" (עברית)
- [ ] "What tasks are due soon?" (אנגלית)

**תוצאה צפויה:**
- Intent: `task_insights`
- תשובה מתייחסת למשימות בפועל
- מזהה משימות דחופות/בעדיפות גבוהה

---

#### 1.2 Potential Create (יצירת משימה - דורש הבהרה)
**בדיקה:** הבוט מזהה כוונה ליצור משימה אבל מבקש פרטים

**הודעות לבדיקה:**
- [ ] "add task" (ללא כותרת)
- [ ] "תוסיף משימה" (ללא כותרת)
- [ ] "create new task" (ללא פרטים)

**תוצאה צפויה:**
- Intent: `potential_create`
- שואל על כותרת המשימה
- מציע אפשרויות (תאריך יעד, עדיפות, וכו')

---

#### 1.3 Potential Update (עדכון משימה - דורש הבהרה)
**בדיקה:** הבוט מזהה כוונה לעדכן אבל מבקש הבהרה

**הודעות לבדיקה:**
- [ ] "update task" (כשיש כמה משימות)
- [ ] "עדכן משימה" (כשיש כמה משימות)
- [ ] "change priority" (ללא ציון משימה)

**תוצאה צפויה:**
- Intent: `potential_update`
- שואל איזו משימה לעדכן
- מציג רשימת משימות רלוונטיות
- שואל מה לשנות

---

#### 1.4 Potential Delete (מחיקת משימה - דורש אישור)
**בדיקה:** הבוט מזהה כוונה למחוק אבל מבקש אישור

**הודעות לבדיקה:**
- [ ] "delete task" (כשיש משימה אחת)
- [ ] "מחק משימה" (כשיש כמה משימות)
- [ ] "remove the first task"

**תוצאה צפויה:**
- Intent: `potential_delete`
- שואל איזו משימה למחוק (אם יש כמה)
- מזהיר על מחיקה לצמיתות
- מבקש אישור

---

### ✅ חלק 2: Clarification Logic - לוגיקת הבהרה

#### 2.1 שאלות הבהרה
**בדיקה:** הבוט שואל שאלות ממוקדות כשיש חוסר בהירות

**תרחישים:**
- [ ] "add task" → שואל על כותרת
- [ ] "update tomorrow's task" (כשיש כמה משימות מחר) → מציג רשימה ושואל איזו
- [ ] "delete urgent task" (כשיש כמה דחופות) → מציג רשימה ושואל איזו

**תוצאה צפויה:**
- שואל שאלה אחת בכל פעם
- מציע אפשרויות רלוונטיות
- לא מנחש או מניח

---

#### 2.2 Task-Aware Responses
**בדיקה:** הבוט מתייחס למשימות ספציפיות

**תרחישים:**
- [ ] "What's urgent?" → מתייחס למשימות בעדיפות גבוהה בפועל
- [ ] "Show me tasks due tomorrow" → מציג משימות עם תאריך מחר
- [ ] "Which task has high priority?" → מציג משימות בעדיפות גבוהה

**תוצאה צפויה:**
- מתייחס למשימות ספציפיות בשם
- משתמש בנתונים אמיתיים (עדיפות, תאריך, סטטוס)
- לא ממציא מידע

---

### ✅ חלק 3: Hebrew Support - תמיכה בעברית

#### 3.1 עברית בכל הכוונות
**בדיקה:** כל הכוונות החדשות עובדות בעברית

**הודעות לבדיקה:**
- [ ] "מה דחוף לי?" → `task_insights`
- [ ] "תוסיף משימה" → `potential_create`
- [ ] "עדכן משימה" → `potential_update`
- [ ] "מחק משימה" → `potential_delete`

**תוצאה צפויה:**
- כל התשובות בעברית
- Intent נכון
- Suggestions בעברית

---

### ✅ חלק 4: Backward Compatibility - תאימות לאחור

#### 4.1 פונקציונליות קיימת
**בדיקה:** כל הפונקציונליות הקיימת עדיין עובדת

**הודעות לבדיקה:**
- [ ] "list my tasks" → `list_tasks`
- [ ] "show summary" → `get_insights`
- [ ] "help" → `unknown` עם suggestions

**תוצאה צפויה:**
- כל ה-intents הקיימים עובדים
- אין regressions
- API contract זהה

---

### ✅ חלק 5: LLM Integration - אינטגרציה עם LLM

#### 5.1 LLM עם Phase 2
**בדיקה:** LLM משתמש בהוראות Phase 2

**תנאים:**
- [ ] `USE_LLM=true` מוגדר
- [ ] `OPENAI_API_KEY` קיים

**הודעות לבדיקה:**
- [ ] "add task" → LLM שואל על כותרת
- [ ] "what's urgent?" → LLM מתייחס למשימות בפועל
- [ ] "update task" → LLM שואל איזו משימה

**תוצאה צפויה:**
- LLM משתמש בהוראות Phase 2
- תשובות TaskGenius-aware
- שואל הבהרות כשיש חוסר בהירות

---

#### 5.2 Fallback ל-Rule-Based
**בדיקה:** Fallback עובד עם Phase 2

**תנאים:**
- [ ] `USE_LLM=false` או LLM נכשל

**הודעות לבדיקה:**
- [ ] "add task" → rule-based שואל על כותרת
- [ ] "what's urgent?" → rule-based מנתח משימות
- [ ] "update task" → rule-based שואל איזו משימה

**תוצאה צפויה:**
- Fallback עובד עם כל הכוונות החדשות
- תשובות בעברית/אנגלית לפי ההודעה
- Intent נכון

---

## סיכום בדיקה

### סטטיסטיקה:
- **סה"כ בדיקות:** 20+
- **Intent types חדשים:** 4 (`task_insights`, `potential_create`, `potential_update`, `potential_delete`)
- **Handlers חדשים:** 3 (`_handle_task_insights`, `_handle_potential_update`, `_handle_potential_delete`)

### קריטריונים להצלחה:
✅ כל ה-intents החדשים מזוהים נכון  
✅ כל ההבהרות עובדות  
✅ תמיכה בעברית בכל הכוונות  
✅ אין regressions בפונקציונליות קיימת  
✅ LLM ו-Rule-Based עובדים עם Phase 2  

---

## הערות לבדיקה

1. **תאימות:** כל הפונקציונליות הקיימת צריכה להמשיך לעבוד
2. **Intent Quality:** הכוונות צריכות להיות מדויקות יותר
3. **Clarification:** הבוט צריך לשאול שאלות ולא לנחש
4. **Task-Aware:** התשובות צריכות להתייחס למשימות בפועל

---

## אם יש בעיות

### בדוק לוגים:
```bash
docker compose logs chatbot-service -f
```

### בדוק intent:
- בדוק את ה-`intent` field בתשובה
- בדוק את ה-`suggestions` field

### בדוק LLM:
- אם `USE_LLM=true`, בדוק שההוראות נשלחות ל-LLM
- אם LLM נכשל, בדוק שה-fallback עובד
