# מדריך: OpenAI Quota - איך לבדוק ולהוסיף Credit

## מה זה Quota?

**Quota** = מגבלת שימוש ב-OpenAI API. זה יכול להיות:
- מגבלת credit (כסף) - נגמר הכסף בחשבון
- מגבלת rate limit - יותר מדי בקשות בפרק זמן קצר
- בעיית billing - בעיה עם אמצעי התשלום

## איך לבדוק את ה-Quota שלך?

### 1. פתח את OpenAI Platform
```
https://platform.openai.com/account/billing
```

### 2. בדוק את ה-Billing
- **Usage & Billing** - ראה כמה השתמשת
- **Payment Method** - בדוק שהכרטיס תקין
- **Credits** - בדוק כמה credit נשאר

### 3. בדוק את ה-API Usage
```
https://platform.openai.com/usage
```
- ראה כמה tokens השתמשת
- ראה כמה כסף הוצאת
- ראה את המגבלות שלך

---

## איך להוסיף Credit?

### אופציה 1: הוסף Payment Method
1. לך ל: https://platform.openai.com/account/billing
2. לחץ על **"Add payment method"**
3. הכנס פרטי כרטיס אשראי
4. OpenAI יגבה אוטומטית כשיש צורך

### אופציה 2: הוסף Credit Manual
1. לך ל: https://platform.openai.com/account/billing
2. לחץ על **"Add credits"** או **"Top up"**
3. בחר סכום
4. שלם

### אופציה 3: בדוק את ה-Plan שלך
1. לך ל: https://platform.openai.com/account/billing/overview
2. בדוק אם יש לך **Free tier** (יש מגבלות)
3. שדרג ל-**Paid plan** אם צריך

---

## איך לבדוק מה הבעיה?

### שגיאת 429 - Rate Limit
**משמעות:** יותר מדי בקשות בפרק זמן קצר

**פתרון:**
- חכה כמה דקות
- או שדרג את ה-plan שלך

### שגיאת Insufficient Quota
**משמעות:** נגמר הכסף/credit

**פתרון:**
- הוסף payment method
- או הוסף credit manual

### שגיאת Billing
**משמעות:** בעיה עם אמצעי התשלום

**פתרון:**
- בדוק שהכרטיס תקין
- עדכן את פרטי התשלום

---

## איך לבדוק מה קורה בקוד?

### בדוק את הלוגים:
```bash
docker compose logs chatbot-service | grep -i quota
docker compose logs chatbot-service | grep -i "429"
docker compose logs chatbot-service | grep -i billing
```

### בדוק את ה-Environment Variables:
```bash
docker compose exec chatbot-service env | grep OPENAI
```

---

## מה קורה עכשיו בקוד?

כשיש בעיית quota:
1. ✅ הבוט מזהה את הבעיה
2. ✅ מציג הודעה למשתמש בצ'אט
3. ✅ נותן קישור ישיר ל-billing page
4. ✅ ממשיך עם rule-based fallback (עם הודעה)

---

## טיפים

1. **הגדר Usage Limits** - תגביל את ההוצאה החודשית
2. **עקוב אחרי Usage** - בדוק כמה אתה משתמש
3. **השתמש ב-gpt-4o-mini** - יותר זול מ-gpt-4
4. **הגדר Alerts** - קבל התראות כשיש בעיות

---

## קישורים שימושיים

- **Billing Dashboard:** https://platform.openai.com/account/billing
- **Usage Dashboard:** https://platform.openai.com/usage
- **API Keys:** https://platform.openai.com/api-keys
- **Documentation:** https://platform.openai.com/docs/guides/error-codes

---

## אם יש בעיות

1. בדוק את הלוגים של chatbot-service
2. בדוק את ה-billing ב-OpenAI
3. נסה API key אחר (אם יש)
4. בדוק את ה-rate limits
