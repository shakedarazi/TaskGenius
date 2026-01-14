# תוכנית בדיקה מקומית - שליחת סיכום שבועי ידני

## מטרת הבדיקה
לבדוק את הפונקציונליות החדשה של שליחת סיכום שבועי לטלגרם באופן ידני דרך ה-UI.

---

## שלב 1: הכנה והפסקת קונטיינרים קיימים

### 1.1 עצירת קונטיינרים קיימים (אם רצים)
```bash
docker compose down
```

### 1.2 ניקוי volumes (אופציונלי - רק אם רוצים DB נקי)
```bash
docker compose down -v
```

### 1.3 בדיקת שדות סביבה (אופציונלי)
אם יש לך `.env` או משתני סביבה, ודא שיש:
- `TELEGRAM_BOT_TOKEN` (אם רוצים לבדוק שליחה אמיתית לטלגרם)

---

## שלב 2: בנייה והפעלת הקונטיינרים

### 2.1 בניית והפעלת כל השירותים
```bash
docker compose up -d --build
```

### 2.2 בדיקת סטטוס הקונטיינרים
```bash
docker compose ps
```

**תוצאה צפויה:**
- `taskgenius-mongodb` - Status: Up, Health: healthy
- `taskgenius-chatbot-service` - Status: Up, Health: healthy  
- `taskgenius-core-api` - Status: Up, Health: healthy

### 2.3 בדיקת health endpoints
```bash
# Core API
curl http://localhost:8000/health

# MongoDB (מתוך הקונטיינר)
docker exec taskgenius-mongodb mongosh --eval "db.adminCommand('ping')"
```

**תוצאה צפויה:**
```json
{"status":"healthy","service":"TASKGENIUS Core API","version":"0.1.0"}
```

---

## שלב 3: הפעלת Frontend (אם לא רץ)

### 3.1 מעבר לתיקיית client
```bash
cd packages/client
```

### 3.2 התקנת dependencies (אם צריך)
```bash
npm install
```

### 3.3 הפעלת dev server
```bash
npm run dev
```

**תוצאה צפויה:**
- Frontend רץ על http://localhost:5173

---

## שלב 4: בדיקת Authentication

### 4.1 הרשמה/התחברות
1. פתח http://localhost:5173
2. היכנס או הירשם
3. ודא שההתחברות הצליחה

### 4.2 בדיקת סטטוס טלגרם
1. לך ל-Settings (אם יש)
2. או בדוק דרך API:
```bash
# קבל token מההתחברות, ואז:
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/telegram/status
```

**תוצאה צפויה:**
```json
{"linked":false,"telegram_username":null,"notifications_enabled":false}
```

---

## שלב 5: קישור טלגרם (אם לא מקושר)

### 5.1 יצירת קוד אימות
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/telegram/link/start
```

**תוצאה צפויה:**
```json
{"code":"ABC123","expires_in_seconds":600}
```

### 5.2 שליחת קוד לבוט טלגרם
1. פתח את הבוט בטלגרם
2. שלח את הקוד שהתקבל
3. ודא שהקישור הצליח

### 5.3 בדיקת סטטוס לאחר קישור
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/telegram/status
```

**תוצאה צפויה:**
```json
{"linked":true,"telegram_username":"your_username","notifications_enabled":false}
```

---

## שלב 6: יצירת משימות לבדיקה

### 6.1 יצירת משימות דרך UI
1. במסך Tasks, צור כמה משימות:
   - משימה אחת עם priority HIGH או URGENT
   - משימה אחת עם deadline בעוד 3 ימים
   - משימה אחת שהושלמה (DONE) היום
   - משימה אחת עם deadline שעבר (overdue)

### 6.2 או דרך API:
```bash
# משימה עם priority גבוהה
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"High Priority Task","priority":"high","status":"open"}' \
  http://localhost:8000/tasks

# משימה עם deadline בעתיד
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Upcoming Task","deadline":"2024-12-25T00:00:00Z","status":"open"}' \
  http://localhost:8000/tasks

# משימה שהושלמה
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Completed Task","status":"done"}' \
  http://localhost:8000/tasks
```

---

## שלב 7: בדיקת Endpoint החדש (API)

### 7.1 בדיקת weekly summary endpoint
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/insights/weekly
```

**תוצאה צפויה:**
```json
{
  "generated_at": "...",
  "period_start": "...",
  "period_end": "...",
  "completed": {"count": 1, "tasks": [...]},
  "high_priority": {"count": 1, "tasks": [...]},
  "upcoming": {"count": 1, "tasks": [...]},
  "overdue": {"count": 0, "tasks": []}
}
```

### 7.2 בדיקת שליחת סיכום לטלגרם (API)
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/telegram/summary/send
```

**תוצאה צפויה:**
```json
{"sent":true,"message":"Summary sent successfully"}
```

**בדיקות:**
- אם לא מקושר לטלגרם: `400 Bad Request` עם הודעה "Telegram account not linked"
- אם מקושר: `200 OK` עם `{"sent":true}`

### 7.3 בדיקת logs
```bash
docker logs taskgenius-core-api --tail 50
```

**חפש:**
- `Sent weekly summary to user ...`
- או שגיאות אם יש

---

## שלב 8: בדיקת UI

### 8.1 בדיקת כפתור Send Summary
1. פתח http://localhost:5173
2. לך למסך Tasks (מסך הבית)
3. ודא שהכפתור "📊 Send Summary" מופיע (רק אם מקושר לטלגרם)

### 8.2 לחיצה על הכפתור
1. לחץ על "📊 Send Summary"
2. ודא שהכפתור משתנה ל-"Sending..." בזמן השליחה
3. בדוק הודעת הצלחה או שגיאה

### 8.3 בדיקת הודעת טלגרם
1. פתח את הבוט בטלגרם
2. ודא שקיבלת את הסיכום השבועי
3. בדוק שהסיכום כולל:
   - ✅ Completed tasks (אם יש)
   - 🔴 High Priority tasks (אם יש)
   - 📅 Upcoming tasks (אם יש)
   - ⚠️ Overdue tasks (אם יש)

---

## שלב 9: בדיקת Edge Cases

### 9.1 משתמש לא מקושר
1. התנתק והתחבר כמשתמש אחר (או בטל קישור)
2. ודא שהכפתור לא מופיע או מופיע disabled

### 9.2 משתמש ללא משימות
1. צור משתמש חדש
2. ודא שהסיכום נשלח עם הודעה "You have no tasks to report this week. Great job! 🎉"

### 9.3 שליחה מרובה
1. שלח סיכום כמה פעמים ברצף
2. ודא שכל שליחה מצליחה (ללא idempotency check)

---

## שלב 10: בדיקת Logs ו-Debugging

### 10.1 בדיקת logs של core-api
```bash
docker logs taskgenius-core-api --tail 100 -f
```

### 10.2 בדיקת שגיאות
```bash
docker logs taskgenius-core-api 2>&1 | grep -i error
```

### 10.3 בדיקת MongoDB
```bash
docker exec taskgenius-mongodb mongosh taskgenius --eval "db.users.find().pretty()"
```

---

## שלב 11: ניקוי (אופציונלי)

### 11.1 עצירת קונטיינרים
```bash
docker compose down
```

### 11.2 ניקוי volumes (מחיקת כל הנתונים)
```bash
docker compose down -v
```

---

## Checklist סופי

- [ ] כל הקונטיינרים רצים ו-healthy
- [ ] Frontend רץ ונגיש
- [ ] משתמש מחובר ומקושר לטלגרם
- [ ] יש משימות לבדיקה (completed, high priority, upcoming, overdue)
- [ ] Endpoint `/insights/weekly` מחזיר סיכום תקין
- [ ] Endpoint `/telegram/summary/send` שולח סיכום
- [ ] כפתור "Send Summary" מופיע ב-UI
- [ ] לחיצה על הכפתור שולחת סיכום
- [ ] הסיכום מגיע לטלגרם
- [ ] הסיכום כולל את כל הסעיפים הנדרשים
- [ ] Edge cases נבדקו (לא מקושר, ללא משימות, שליחה מרובה)

---

## פתרון בעיות נפוצות

### כפתור לא מופיע
- ודא שהמשתמש מקושר לטלגרם (`/telegram/status` מחזיר `linked: true`)
- רענן את הדף
- בדוק console בדפדפן לשגיאות

### שליחה נכשלת
- בדוק `docker logs taskgenius-core-api` לשגיאות
- ודא ש-`TELEGRAM_BOT_TOKEN` מוגדר (אם צריך)
- בדוק שהמשתמש מקושר לטלגרם

### סיכום לא מגיע לטלגרם
- בדוק שהבוט רץ ופעיל
- בדוק webhook בטלגרם
- בדוק logs של core-api

---

## הערות

- הבדיקה לא דורשת `TELEGRAM_BOT_TOKEN` לבדיקת ה-endpoint, אבל דורשת לשליחה אמיתית
- הסיכום האוטומטי (scheduler) עדיין רץ כל 7 ימים (או לפי `TELEGRAM_WEEKLY_SUMMARY_INTERVAL_SECONDS`)
- שליחה ידנית לא מונעת שליחה אוטומטית (אין idempotency check)
