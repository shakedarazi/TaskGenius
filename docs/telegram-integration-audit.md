## 1) Executive Summary

- **סטטוס טלגרם נוכחי**: PARTIAL – קיימים מודולים מלאים ל‑webhook, עיבוד הודעות ושליחת הודעות דרך Bot API, אך אין מיפוי אמיתי ל־DB, אין חיבור מה־UI, ואין scheduler להודעות/סיכומים.
- **מה קיים היום**: נתיב `POST /telegram/webhook` ב‑FastAPI שמעביר עדכוני טלגרם ל־`TelegramService`, שמתממשק ל־`ChatService` ולטאסקים; מתאם `TelegramAdapter` ששולח הודעות ל‑Telegram Bot API בעזרת `httpx`; מודלי Pydantic לעדכון/הודעה/שליחה; בדיקות יחידה לאדפטר, לסרוויס ול‑webhook; קונפיגורציה ל‑`TELEGRAM_BOT_TOKEN`.
- **מה חסר**: מיפוי אמיתי בין משתמש אפליקציה ל־Telegram user/chat ב‑MongoDB; כל UI לחיבור טלגרם; זרימת וידוא (verification) בטוחה; scheduler לסיכום שבועי; טריגרים לאירועי create/update/delete של טאסקים; תיעוד תפעולי מלא.
- **חסמים עיקריים**: שכבת המיפוי ב‑`TelegramService` היא in-memory בלבד (לא פרסיסטנטית); אין שדות במודל המשתמש או במסמכי הטאסקים למזהה טלגרם / chat_id; אין תהליך provisioning של webhook (רק endpoint); אין אינטגרציה בין UI ל‑API לצורך opt‑in/opt‑out.
- **יכולות קיימות בפועל**: קבלת webhook מטלגרם, ניתוב הטקסט דרך מנוע הצ’אט הקיים, ושליחת תשובה אל אותו `chat_id` (בכפוף ל‑`TELEGRAM_BOT_TOKEN` תקין).
- **סיכון/השפעה**: האינטגרציה מתאימה כרגע בעיקר ל־PoC או בדיקות CI; בפרודקשן תיתכן אובדן מיפויים אחרי ריסטארט והיעדר שליטה של המשתמש על חיבור/ניתוק טלגרם.
- **תשתית קיימת לשדרוג**: הפרדה ברורה למודול `app.telegram.*`, שימוש בקונפיגורציית `settings`, בדיקות יחידה וקובצי docs קיימים (לוגיקת insights ו‑weekly), מה שמאפשר הרחבה יחסית ממוקדת.

---

## 2) Current Architecture (Repository-Specific)

### רכיבים מעורבים

- **`services/core-api/app/main.py`**
  - כולל את `telegram_router` דרך `from app.telegram import telegram_router` ושורת `app.include_router(telegram_router)` (שורות 19, 93–94).
- **`services/core-api/app/telegram/router.py`**
  - מגדיר את הנתיבים `POST /telegram/webhook` ו‑`GET /telegram/webhook`.
  - משתמש ב‑`TelegramService` ו‑`TaskRepositoryInterface`.
- **`services/core-api/app/telegram/service.py`**
  - `TelegramService` – שכבת business logic לעדכוני webhook, מיפוי משתמשים, קריאה ל‑`ChatService`, ושליחת תשובות דרך `TelegramAdapter`.
- **`services/core-api/app/telegram/adapter.py`**
  - `TelegramAdapter` – אחראי על שליחת הודעות אל Telegram Bot API באמצעות `httpx.AsyncClient`.
- **`services/core-api/app/telegram/schemas.py`**
  - מודלים `TelegramUser`, `TelegramMessage`, `TelegramUpdate`, `TelegramSendMessageRequest`, `TelegramSendMessageResponse`.
- **`services/core-api/app/config.py`**
  - קונפיגורציית `TELEGRAM_BOT_TOKEN` (שורה 33).
- **`services/core-api/tests/test_telegram.py`**
  - בדיקות עבור `TelegramAdapter`, `TelegramService` ו‑webhook.
- **`services/core-api/app/chat/service.py`**
  - `ChatService` – מנוע השיחה שמשמש גם את טלגרם; מפעיל את chatbot‑service ואינסייטים.

### תרשים זרימת נתונים (טקסטואלי)

```text
Telegram Bot
    |
    | HTTPS webhook (update JSON)
    v
FastAPI (core-api)
  /telegram/webhook  (router.py)
    |
    | Depends(get_telegram_service) --> TelegramService(db)
    | Depends(get_task_repository)  --> TaskRepositoryInterface
    v
TelegramService.process_webhook_update(update, task_repo)
    |
    |-- Extract text, telegram_user_id, chat_id
    |-- _get_or_create_user_mapping(telegram_user_id)  [in-memory mapping only]
    |   |
    |   v
    |   app_user_id (or None)
    |
    |-- if no app_user_id:
    |      TelegramAdapter.send_message(chat_id, "please register...")
    |      return
    |
    |-- ChatService.process_message(user_id=app_user_id, message=text, task_repository)
    |      |
    |      v
    |    ChatResponse(reply="...", intent="...")
    |
    |-- TelegramAdapter.send_message(chat_id, ChatResponse.reply)
    v
Telegram Bot delivers message to end-user chat
```

### מיקום קונפיגורציה

- **Environment variable**
  - `TELEGRAM_BOT_TOKEN` – מוגדר ב‑`services/core-api/app/config.py` ומועבר אל `TelegramAdapter` דרך `settings.TELEGRAM_BOT_TOKEN`.
  - מופיע גם ב‑`docker-compose.yml` בשורה `- TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}`.
- **מסמכי תיעוד קיימים**
  - `docs/how_to_run_local.md` – מציין את `TELEGRAM_BOT_TOKEN` כ‑optional לצורך פונקציונליות webhook.
  - `phases/phase-05.telegram.md` – מתאר ברמת high‑level את שלב אינטגרציית טלגרם (config בלבד, ללא קוד UI).

### מנגנוני רקע / Scheduler

- אין שימוש ב‑APScheduler, Celery, cron, או worker אחר לתזמון הודעות טלגרם.
- הקוד היחיד שקשור ל‑weekly summary נמצא ב‑`services/core-api/app/insights/*` וב‑`services/core-api/app/chat/service.py` ( weekly summary מחושב לפי בקשת משתמש בצ'אט), אבל **לא** קיים קישור ל‑Telegram scheduler.
- מסקנה: **אין Scheduler ייעודי לטלגרם** בקוד הנוכחי.

---

## 3) What the Telegram Integration Currently Does

### יכולות נתמכות

1. **קבלת webhook מטלגרם**
   - **קובץ**: `services/core-api/app/telegram/router.py`
   - **נקודת כניסה**: `@router.post("/webhook") -> telegram_webhook`
   - **תפקיד**: לקבל `TelegramUpdate`, להזרים אותו ל‑`TelegramService.process_webhook_update`, ולהחזיר `{ "ok": True/False }`.

2. **בדיקת webhook (info endpoint)**
   - **קובץ**: `services/core-api/app/telegram/router.py`
   - **נקודת כניסה**: `@router.get("/webhook") -> telegram_webhook_info`
   - **תפקיד**: להחזיר JSON עם `{"status": "webhook_endpoint", "service": "TASKGENIUS Core API"}` לבדיקה חיצונית.

3. **עיבוד הודעות נכנסות והעברתן ל‑ChatService**
   - **קובץ**: `services/core-api/app/telegram/service.py`
   - **נקודת כניסה**: `TelegramService.process_webhook_update(update, task_repository)`
   - **זרימה**:
     - בודק אם ל‑`update.message` יש `text`; אם אין – מתעלם (שורות 51–53).
     - שולף `telegram_user_id = update.message.from_user.id`, `message_text = update.message.text`, `chat_id = update.message.chat.get("id")` (שורות 55–57).
     - קורא ל‑`_get_or_create_user_mapping(telegram_user_id)` (שורות 59–62).
     - אם אין `app_user_id` – שולח הודעה מסבירה למשתמש דרך `TelegramAdapter.send_message` (שורות 64–70).
     - אם יש `app_user_id` – קורא ל‑`ChatService.process_message(user_id=app_user_id, message=message_text, task_repository=...)` (שורות 72–77) ומחזיר `ChatResponse`.
     - אחר כך שולח את `chat_response.reply` בחזרה לטלגרם דרך `TelegramAdapter.send_message(chat_id, text)` (שורות 79–82).

4. **שליחת הודעות ל‑Telegram Bot API**
   - **קובץ**: `services/core-api/app/telegram/adapter.py`
   - **נקודת כניסה**: `TelegramAdapter.send_message(chat_id, text, parse_mode=None)`
   - **התנהגות**:
     - אם אין `bot_token` (לא הוגדר `TELEGRAM_BOT_TOKEN`), הפונקציה מחזירה `TelegramSendMessageResponse(ok=False, result=None)` בלי לזרוק שגיאה (שורות 56–61).
     - אם יש token, נבנית בקשת `POST` ל‑`https://api.telegram.org/bot{token}/sendMessage` עם JSON `{chat_id, text, parse_mode?}` (שורות 63–71), נשלחת באמצעות `httpx.AsyncClient`, והתגובה מפוענחת ל‑`TelegramSendMessageResponse`.
     - במקרה של שגיאת HTTP – מוחזר `ok=False` (שורות 72–83).

5. **מודלי נתונים ל‑Webhook ול‑SendMessage**
   - **קובץ**: `services/core-api/app/telegram/schemas.py`
   - `TelegramUser`, `TelegramMessage`, `TelegramUpdate`, `TelegramSendMessageRequest`, `TelegramSendMessageResponse`.
   - תואמים למבנה ה‑JSON הסטנדרטי של Telegram (כולל `from` כ‑alias ל‑`from_user`).

6. **בדיקות יחידה ואינטגרציה ל‑Telegram**
   - **קובץ**: `services/core-api/tests/test_telegram.py`
   - בודק:
     - `TelegramAdapter.send_message` במצבי הצלחה, ללא token, ושגיאת API.
     - `TelegramService.process_webhook_update` עם/בלי mapping, ו‑no‑text.
     - `POST /telegram/webhook` ו‑`GET /telegram/webhook` מקבלים ועונים כראוי.

### מה **לא** קיים כרגע

- אין לוגיקה שמקבלת webhook מטלגרם ומקשרת אותו אוטומטית למשתמש רשום (חסר flow של אימות/קישור).
- אין הודעות מתוזמנות (weekly summary או התראות אוטומטיות).
- אין תמיכה רשמית בפקודות בוט (כגון `/start`, `/help`) – הכל מטופל כטקסט חופשי דרך `ChatService`.

---

## 4) How to Run It (Step-by-Step)

### תלויות ותשתיות

- **DB**: MongoDB (משמש את core‑api ואת task repository).
- **שירותים נלווים**:
  - `chatbot-service` (מתואר ב‑`docker-compose.yml`, נצרך על ידי `ChatService`).
- **סודות/משתני סביבה נדרשים**
  - `TELEGRAM_BOT_TOKEN` – נדרש כדי לשלוח הודעות אמיתיות דרך הבוט.
  - יתר משתני הסביבה (DB, JWT וכו') – כפי שמתועד ב‑`docs/how_to_run_local.md`.

### פקודות הרצה (מבוסס על הקיים)

1. **הרצת כל המערכת בדוקר**  
   - קובץ: `docker-compose.yml`  
   - פקודה טיפוסית (מתועדת ב‑`docs/how_to_run_local.md`):  
     ```bash
     docker compose up core-api chatbot-service
     ```  
   - ודא ש‑`TELEGRAM_BOT_TOKEN` מוגדר בסביבה או בקובץ `.env`.

2. **הרצת core-api לוקאלית (ללא docker)**  
   - קובץ: `services/core-api/app/main.py`  
   - קיימת אפליקציית FastAPI שמוגדרת שם; ניתן להריץ, לדוגמה:  
     ```bash
     cd services/core-api
     uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
     ```
   - (הפקודה עצמה איננה מתועדת בצורה ישירה – אם אין `uvicorn` או סקריפט מתאים, זה נדרש להוספה; כרגע זה **MISSING** במסמכי README).

3. **הגדרת webhook בטלגרם** – **MISSING**
   - בקוד אין סקריפט/פקודה שמגדירים `setWebhook` בטלגרם.
   - נדרש להגדיר מחוץ לריפו, לדוגמה:  
     ```bash
     curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<public-host>/telegram/webhook"
     ```  
   - שלב זה לא מתועד בקבצי `docs/*` – יש להוסיף הסבר בעתיד.

4. **וולידציה בסיסית של ה‑webhook**
   - אחרי שה‑core-api רץ:
     - `GET /telegram/webhook` – אמור להחזיר JSON עם `status: "webhook_endpoint"`.
     - `POST /telegram/webhook` עם update דמה (כמו ב‑`test_telegram.py` שורות 209–222) אמור להחזיר `{ "ok": true/false }` בהתאם ל‑logic.

### שלבים חסרים/מסומנים כ‑MISSING

- סקריפט או תיעוד רשמי להגדרת webhook באמצעות `setWebhook`.
- הוראות מפורטות ב‑README להפעלת אינטגרציית טלגרם (נרמזות ב‑`docs/how_to_run_local.md` אך לא מפורטות).
- תיעוד UI/flow למיפוי משתמש → Telegram user (כרגע אין).

---

## 5) Validation & Observability

### איך לוודא שהודעות נשלחות בפועל

- **לוגים**:
  - `TelegramAdapter.send_message` משתמש ב‑`httpx.AsyncClient` אך לא כותב לוגים מפורשים – ניתן להסתמך על לוגים ברמת uvicorn/httpx או להוסיף לוגים בעתיד.
  - בדיקות ב‑`test_telegram.py` מבטיחות שהקריאה ל‑`send_message` מתבצעת, אך לא מדגימות לוגים.
- **בדיקות ידניות**:
  1. הפעל core‑api עם `TELEGRAM_BOT_TOKEN` תקין.
  2. ודא שה‑webhook מוגדר ל‑`/telegram/webhook`.
  3. שלח הודעה לבוט; צפוי:
     - אם אין mapping למשתמש – לקבל הודעה "Please register in the web application first to use Telegram integration."
     - אם קיים mapping (דרך `TelegramService.set_user_mapping` בתרחיש ניסוי) – לקבל תשובה מהצ’אטבוט (`ChatResponse.reply`).

### Endpoints בריאות/אבחון

- `GET /telegram/webhook` – מחזיר מידע בסיסי על webhook (נוכחות/סטטוס).
- אין endpoint ייעודי ל‑health של טלגרם מעבר לכך.

### היכן יופיעו שגיאות

- בתוך `telegram_webhook` ב‑`router.py`, בלוק ה‑`try/except` מחזיר `{ "ok": False, "error": str(e) }` אך אינו כותב לוגים.
- שגיאות של `httpx` בתוך `TelegramAdapter` נבלעות ומוחזר `ok=False` ללא לוג.
- אין metricים או tracing ייעודיים (Prometheus/OpenTelemetry וכו') לאינטגרציית טלגרם.

---

## 6) Gap Analysis (What’s Missing)

| Needed for “Fully Working Telegram Integration”                          | Present? (Yes/Partial/No) | Evidence (file path)                                      | What’s missing / next step                                                                                   |
|-------------------------------------------------------------------------|---------------------------|-----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| Bot token configuration                                                | Partial                   | `services/core-api/app/config.py`, `docker-compose.yml`, `docs/how_to_run_local.md` | יש `TELEGRAM_BOT_TOKEN`, אך אין תיעוד מלא ל‑setWebhook, רוטציית סודות, וסביבות שונות.                      |
| Webhook or polling implementation                                      | Partial                   | `services/core-api/app/telegram/router.py`               | יש webhook endpoints, אך אין provisioning של webhook (setWebhook) ואין polling כחלופה.                      |
| Mapping Telegram user/chat to app user                                 | Partial                   | `services/core-api/app/telegram/service.py`              | מיפוי in-memory בלבד דרך `_user_mappings`; צריך שכבת persistence במונגו וטבלת/קולקציית mapping מסודרת.     |
| Persistence in DB (schema, migrations)                                 | No                        | (אין קבצי schema/migrations הקשורים ל‑telegram)          | הוספת קולקציה `user_telegram_mappings` או שדות ב‑users; עדכון models ו‑repository בהתאם.                   |
| Scheduler for weekly summary                                           | No                        | (אין scheduler בקוד; weekly summary רק דרך chat/insights)| נדרש job מתוזמן (APScheduler / cron חיצוני) שקורא ל‑insights ול‑TelegramService לשליחת סיכומים.           |
| Event-driven notifications for task create/update                      | No                        | `services/core-api/app/tasks/*`                          | אין hooks ששולחים התראות לטלגרם על create/update/delete; צריך להוסיף service/observer שיקרא ל‑TelegramAdapter. |
| Idempotency / duplicate prevention                                     | No                        | (אין קוד ייעודי)                                         | אין שימוש ב‑update_id, message_id או טבלת dedupe; נדרש מנגנון למניעת שליחה כפולה (למשל אחסון update_id אחרון). |
| Rate limiting / retries / dead-letter behavior (if queues exist)       | No                        | (אין queues/worker בקוד טלגרם)                           | אם ייכנס תור (queue) בעתיד – יש להגדיר rate limit, retries ו‑DLQ; כרגע הכל סינכרוני דרך httpx בלבד.        |
| UI flow לחיבור/ניתוק טלגרם                                             | No                        | (רק backend; אין קבצי UI רלוונטיים)                     | הוספת כפתור/מסך ב‑client, endpoint תואם ב‑core‑api, ושדות שמורים ב‑DB.                                      |
| Observability (logs/metrics ספציפיים לטלגרם)                           | No                        | `telegram/router.py`, `telegram/adapter.py`              | הוספת לוגים ברמת info/warn ו‑metrics בסיסיים (מדי ספירה לכשלונות/הצלחות, latency).                         |

---

## 7) Upgrade Guide: “Connect Telegram in UI + Store in DB + Enable Scheduler + Live Task Notifications”

### A) Minimal Design

- **שדות נתונים נדרשים (למשתמש)** – בקולקציית משתמשים (שאינה קיימת במפורש בריפו, אבל נרמזת דרך auth):
  - `telegram_user_id: Optional[int]`
  - `telegram_chat_id: Optional[int]`
  - `telegram_username: Optional[str]`
  - `telegram_connected_at: Optional[datetime]`
  - `telegram_notifications_enabled: bool` (ברירת מחדל `False`)
- **שדות נתונים אפשריים נוספים (למיפוי נפרד)**:
  - קולקציה `user_telegram_mappings` עם `{ _id, user_id, telegram_user_id, telegram_chat_id, created_at }`.
- **שיקולי אבטחה**:
  - אין להסתמך על username בלבד (ניתן לשינוי); עדיף `telegram_user_id` + תהליך וידוא.
  - Flow מומלץ:
    1. המשתמש לוחץ “Connect Telegram” ב‑UI.
    2. השרת מייצר `verification_code` חד‑פעמי (קצר‑חיים) ושומר אותו ב‑DB.
    3. המשתמש שולח את הקוד לבוט בטלגרם.
    4. `TelegramService` מזהה את הקוד, מאמת את המשתמש המחובר, וקושר את `telegram_user_id` ו‑`chat_id` למשתמש.
  - יש להיזהר מהתחזות: ללא code flow, כל מי שיודע username יכול להתחזות.

### B) File Change Map (MOST IMPORTANT)

> הערה: אין לשנות קבצים בפועל לפי משימת ה‑audit הזו; להלן מפת קבצים צפויה לפיתוח עתידי.

#### 1. כפתור UI: “Connect Telegram”

- **קבצים מועמדים (frontend)**:
  - `packages/client/src/components/Layout.tsx` – ה‑navigation bar שבו כבר יש כפתורי Login/Register/Tasks; ניתן להוסיף שם קישור/כפתור ל‑“Settings” או “Connect Telegram”.
  - `packages/client/src/pages/TasksPage.tsx` או דף הגדרות ייעודי (אם קיים בעתיד) – מקום טבעי לכפתור “Connect Telegram”.
- **סוג שינוי**:
  - הוספת כפתור/קישור שמנווט לעמוד הגדרות/חיבור טלגרם.

#### 2. אינפוט UI להזנת username / תהליך וידוא

- **קבצים מועמדים (frontend)**:
  - `packages/client/src/pages/<SettingsPage>.tsx` – לא קיים כרגע; יהיה צורך ליצור דף חדש להגדרות משתמש.
  - חלופה מינימלית: בתוך `TasksPage.tsx` כחלק מאיזור הגדרות, עם טופס קטן.
- **סוג שינוי**:
  - הוספת טופס להזנת username או הצגת `verification_code` שהשרת יוצר.

#### 3. Endpoint backend לשמירת מזהי טלגרם ב‑DB

- **קבצים מועמדים (backend)**:
  - `services/core-api/app/auth/router.py` – מקום טבעי להוסיף route מאובטח כמו `POST /auth/telegram/link` למשתמש מחובר.
  - `services/core-api/app/auth/models.py` ו‑`services/core-api/app/auth/repository.py` – הרחבת מודל המשתמש/קולקציה כדי לכלול שדות טלגרם.
  - לחלופין, מודול חדש `services/core-api/app/telegram/models.py` + `repository.py` עבור קולקציית mapping (ייתכן שכבר היה קיים ונמחק לפי רשימת ה‑deleted_files).
- **סוג שינוי**:
  - הוספת Pydantic schema ל‑link/unlink.
  - הוספת פעולת upsert בקולקציית mapping.
  - עדכון `TelegramService._get_or_create_user_mapping` להשתמש ב‑MongoDB במקום in‑memory.

#### 4. Scheduler activation (weekly summary)

- **קבצים מועמדים**:
  - `services/core-api/app/insights/service.py` – כבר יודע לייצר `WeeklySummary` על‑פי טאסקים.
  - `services/core-api/app/main.py` – מקום טוב לאתחול scheduler (APScheduler או job אחר).
  - קובץ חדש אפשרי: `services/core-api/app/scheduler.py` – הגדרת jobs (למשל, `send_weekly_telegram_summary()`).
- **סוג שינוי**:
  - הוספת job שמתזמן הרצה (למשל, אחת לשבוע) שמאתר משתמשים עם `telegram_notifications_enabled=True`, קורא ל‑`insights_service.generate_weekly_summary`, ושולח אפשרות לסיכום דרך `TelegramAdapter`.

#### 5. Event hooks להודעות Live על create/update של טאסקים

- **קבצים מועמדים**:
  - `services/core-api/app/tasks/service.py` – נקודת ריכוז ללוגיקת create/update/delete; מתאים להוסיף בו hooks אחרי פעולת `create_task`, `update_task`, `delete_task`.
  - `services/core-api/app/telegram/service.py` או שירות חדש `TaskNotificationService` – שיכלול לוגיקה של “איזה טקסט לשלוח למשתמש”.
  - ייתכן שיהיה צורך בגישה ל‑user repository כדי למשוך את `telegram_chat_id` של בעל המשימה.
- **סוג שינוי**:
  - אחרי יצירת טסק: קריאה ל‑notification service שיבדוק אם המשתמש מחובר לטלגרם ויעשה `.send_message(...)`.
  - אחרי עדכון סטטוס (למשל ל‑DONE): שליחת הודעה מתאימה.

### C) Implementation Notes

- **סגנון קוד נוכחי**:
  - core‑api כתוב ב‑FastAPI Async; repositoryים משתמשים ב‑`motor` (MongoDB async).
  - `TelegramService` ו‑`TelegramAdapter` הם async ומבודדים היטב; מומלץ להמשיך באותו pattern.
- **מיקום מומלץ ל‑“Telegram service” מורחב**:
  - שכבה קיימת: `TelegramService` – ניתן להרחיב אותה כך שתטפל גם ב‑notifications ואולי באינטראקציות נוספות.
  - לחלופין, ליצור שירות נוסף `TelegramNotificationService` שייקרא מתוך `tasks/service.py`, וישתמש ב‑`TelegramAdapter` (תוך שמירה על תלות הפוכה: tasks לא יודעים על chat).
- **מניעת שליחה כפולה (idempotency)**:
  - לנצל את `update_id` של Telegram (ב‑`TelegramUpdate`) ולשמור טבלת/קולקציית `processed_updates` עם `{update_id, chat_id, processed_at}`.
  - לפני עיבוד update חדש, לבדוק אם `update_id` כבר טופל.
  - עבור התראות מתוך המערכת (לא דרך webhook), ניתן להשתמש ב‑`task_id` + סוג אירוע (`created/updated/completed`) כ־idempotency key בטבלה ייעודית (כדי לא לשלוח שוב במקרה של retry).

---

## 8) Appendix: Evidence Index

- `services/core-api/app/main.py` – רישום `telegram_router` לאפליקציית FastAPI.
- `services/core-api/app/telegram/__init__.py` – מייצא את `telegram_router` עבור main.
- `services/core-api/app/telegram/router.py` – מגדיר את נתיבי `/telegram/webhook` (POST ו‑GET).
- `services/core-api/app/telegram/service.py` – לוגיקת עיבוד webhook ומיפוי משתמשים לוגי (in‑memory).
- `services/core-api/app/telegram/adapter.py` – מתאם שליחת הודעות ל‑Telegram Bot API עם טיפול ב‑token חסר ושגיאות HTTP.
- `services/core-api/app/telegram/schemas.py` – מודלי Pydantic ל‑Telegram (User, Message, Update, SendMessageRequest/Response).
- `services/core-api/app/config.py` – הגדרת `TELEGRAM_BOT_TOKEN` בקונפיגורציה.
- `docker-compose.yml` – מעביר `TELEGRAM_BOT_TOKEN` כ‑environment variable לשירות core‑api.
- `docs/how_to_run_local.md` – מזכיר את `TELEGRAM_BOT_TOKEN` ואת היותו optional; רמז להפעלת webhook.
- `services/core-api/tests/test_telegram.py` – בדיקות יחידה לאדפטר/סרוויס/נתיבי webhook.
- `services/core-api/app/chat/service.py` – מנוע הצ’אט ש‑TelegramService משתמש בו לניתוב הודעות.
- `services/core-api/app/insights/*` – לוגיקת weekly insights; רלוונטית לשדרוג עתידי לסיכומים שבועיים בטלגרם.

