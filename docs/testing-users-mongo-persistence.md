# בדיקת Persistence של Users + Telegram Linkage

## מטרת הבדיקה
לוודא ש:
1. Users נשמרים ב-MongoDB ולא נעלמים ב-restart
2. Telegram linkage נשמר ב-`user.telegram` field
3. אחרי restart, המשתמש עדיין קיים והחיבור לטלגרם עדיין פעיל

---

## שלב 1: בדיקת מצב נוכחי ב-MongoDB

### 1.1 התחבר ל-MongoDB
```bash
docker-compose exec mongodb mongosh
```

### 1.2 בחר את ה-DB
```javascript
use taskgenius
```

### 1.3 בדוק מה יש ב-collections
```javascript
// רשימת כל ה-collections
show collections

// בדוק אם יש users collection
db.users.find()

// בדוק אם יש user_telegram_links (ישן - לא צריך להיות בשימוש)
db.user_telegram_links.find()
```

**תוצאה צפויה:**
- `users` collection - יכול להיות ריק או עם משתמשים ישנים
- `user_telegram_links` - יכול להיות עם נתונים ישנים (לא משפיע)

---

## שלב 2: ניקוי נתונים ישנים (אופציונלי - רק אם רוצים התחלה נקייה)

### 2.1 מחק נתונים ישנים
```javascript
// מחק users ישנים (אם יש)
db.users.deleteMany({})

// מחק user_telegram_links ישנים (אם יש)
db.user_telegram_links.deleteMany({})

// מחק verification codes ישנים
db.telegram_verification_codes.deleteMany({})
```

### 2.2 צא מ-MongoDB
```javascript
exit
```

---

## שלב 3: אתחל את core-api

### 3.1 ודא ש-core-api רץ
```bash
docker-compose up -d core-api
```

### 3.2 בדוק שהכל תקין
```bash
docker-compose ps core-api
```

צריך לראות `STATUS ... Up ... (healthy)`

### 3.3 בדוק logs
```bash
docker-compose logs core-api --tail 50
```

צריך לראות:
- `Application startup complete`
- `Weekly summary scheduler started` (אם `TELEGRAM_WEEKLY_SUMMARY_ENABLED=true`)

---

## שלב 4: יצירת משתמש חדש דרך ה-API

### 4.1 Register משתמש חדש
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"testuser\", \"password\": \"testpass123\"}"
```

**תוצאה צפויה:**
```json
{"message": "User registered successfully"}
```

### 4.2 Login לקבלת token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"testuser\", \"password\": \"testpass123\"}"
```

**תוצאה צפויה:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**שמור את ה-token** - נצטרך אותו לשלבים הבאים.

---

## שלב 5: בדיקה ב-MongoDB שהמשתמש נשמר

### 5.1 התחבר שוב ל-MongoDB
```bash
docker-compose exec mongodb mongosh
```

### 5.2 בחר DB
```javascript
use taskgenius
```

### 5.3 בדוק שהמשתמש נשמר
```javascript
db.users.find().pretty()
```

**תוצאה צפויה:**
```json
{
  "_id": "some-uuid",
  "username": "testuser",
  "password_hash": "$2b$...",
  "created_at": ISODate("2026-01-14T..."),
  "telegram": null  // עדיין לא מקושר
}
```

**חשוב:** אם אתה רואה את המשתמש כאן, זה אומר שהוא נשמר ב-MongoDB.

---

## שלב 6: חיבור טלגרם דרך ה-API

### 6.1 Generate verification code
```bash
curl -X POST http://localhost:8000/telegram/link/start \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

**תוצאה צפויה:**
```json
{
  "code": "AbCdEf",
  "expires_in_seconds": 600
}
```

**שמור את ה-code** (למשל: `AbCdEf`)

### 6.2 בדוק status לפני linking
```bash
curl -X GET http://localhost:8000/telegram/status \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**תוצאה צפויה:**
```json
{
  "linked": false,
  "telegram_username": null,
  "notifications_enabled": false
}
```

### 6.3 שלח את ה-code לבוט בטלגרם
1. פתח את הטלגרם
2. מצא את הבוט שלך
3. שלח את ה-code (למשל: `AbCdEf`)

**תוצאה צפויה:**
הבוט אמור להגיב:
```
✅ Account linked successfully! You can now use Telegram to manage your tasks. Send /help to see available commands.
```

### 6.4 בדוק status אחרי linking
```bash
curl -X GET http://localhost:8000/telegram/status \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**תוצאה צפויה:**
```json
{
  "linked": true,
  "telegram_username": "your_telegram_username",
  "notifications_enabled": false
}
```

---

## שלב 7: בדיקה ב-MongoDB שהחיבור נשמר

### 7.1 בדוק ב-MongoDB
```javascript
db.users.find().pretty()
```

**תוצאה צפויה:**
```json
{
  "_id": "same-uuid-as-before",
  "username": "testuser",
  "password_hash": "$2b$...",
  "created_at": ISODate("2026-01-14T..."),
  "telegram": {
    "telegram_user_id": 123456789,
    "telegram_chat_id": 123456789,
    "telegram_username": "your_telegram_username",
    "notifications_enabled": false,
    "linked_at": ISODate("2026-01-14T...")
  }
}
```

**חשוב:** ה-`telegram` field צריך להיות בתוך ה-user document, לא ב-collection נפרד.

---

## שלב 8: RESTART - הבדיקה המרכזית

### 8.1 Restart את core-api
```bash
docker-compose restart core-api
```

או לחלופין:
```bash
docker-compose stop core-api
docker-compose start core-api
```

### 8.2 המתן שהקונטיינר יעלה
```bash
docker-compose ps core-api
```

צריך לראות `STATUS ... Up ... (healthy)`

### 8.3 בדוק logs
```bash
docker-compose logs core-api --tail 30
```

צריך לראות:
- `Application startup complete`
- אין שגיאות

---

## שלב 9: בדיקה שהמשתמש עדיין קיים

### 9.1 נסה להתחבר עם אותו username/password
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"testuser\", \"password\": \"testpass123\"}"
```

**תוצאה צפויה:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**אם זה עובד** → המשתמש נשמר ב-MongoDB.

**אם זה לא עובד** → יש בעיה, צריך לבדוק logs.

### 9.2 בדוק status של טלגרם (עם ה-token החדש)
```bash
curl -X GET http://localhost:8000/telegram/status \
  -H "Authorization: Bearer NEW_TOKEN_HERE"
```

**תוצאה צפויה:**
```json
{
  "linked": true,
  "telegram_username": "your_telegram_username",
  "notifications_enabled": false
}
```

**אם זה עובד** → החיבור לטלגרם נשמר ב-MongoDB.

---

## שלב 10: בדיקה סופית ב-MongoDB

### 10.1 התחבר ל-MongoDB
```bash
docker-compose exec mongodb mongosh
```

### 10.2 בדוק את המשתמש
```javascript
use taskgenius
db.users.find().pretty()
```

**תוצאה צפויה:**
- אותו `_id` כמו לפני ה-restart
- אותו `username`
- אותו `telegram` object עם כל הפרטים

### 10.3 בדוק שהבוט עדיין מזהה אותך
1. שלח הודעה לבוט בטלגרם (למשל: `hi`)
2. הבוט אמור להגיב (כי הוא מזהה את `telegram_user_id`)

---

## שלב 11: בדיקת Weekly Summary (אופציונלי)

אם יש לך `TELEGRAM_WEEKLY_SUMMARY_ENABLED=true` ב-`.env`:

### 11.1 הפעל notifications
```bash
curl -X PATCH http://localhost:8000/telegram/notifications \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d "{\"enabled\": true}"
```

### 11.2 צור כמה tasks
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Test Task\", \"status\": \"OPEN\", \"priority\": \"HIGH\"}"
```

### 11.3 בדוק logs של scheduler
```bash
docker-compose logs -f core-api | findstr -i "weekly\|scheduler"
```

תוך דקה-שתיים (אם `TELEGRAM_WEEKLY_SUMMARY_INTERVAL_SECONDS=60`), אמור להגיע סיכום שבועי בטלגרם.

---

## סיכום - מה צריך לעבוד

✅ **Users נשמרים ב-MongoDB** - אחרי restart, login עובד  
✅ **Telegram linkage נשמר** - אחרי restart, `/telegram/status` מחזיר `linked: true`  
✅ **הבוט מזהה אותך** - אחרי restart, הודעות לבוט עובדות  
✅ **Weekly summaries** - אם מופעל, עובד עם הנתונים הנשמרים

---

## אם משהו לא עובד

### בעיה: Login לא עובד אחרי restart
**בדוק:**
- האם `users` collection קיים ב-MongoDB?
- האם יש documents ב-`users`?
- מה יש ב-logs של `core-api`?

### בעיה: Telegram status מחזיר `linked: false` אחרי restart
**בדוק:**
- האם ה-`telegram` field קיים ב-user document ב-MongoDB?
- האם ה-`user_id` ב-token תואם ל-`_id` ב-MongoDB?

### בעיה: הבוט לא מזהה אותך
**בדוק:**
- האם `telegram.telegram_user_id` ב-MongoDB תואם ל-telegram_user_id שלך?
- מה יש ב-logs של `core-api` כשאתה שולח הודעה?

---

## פקודות שימושיות לבדיקה מהירה

```bash
# בדוק users ב-MongoDB
docker-compose exec mongodb mongosh --eval "use taskgenius; db.users.find().pretty()"

# בדוק logs
docker-compose logs -f core-api

# בדוק health
curl http://localhost:8000/health
```
