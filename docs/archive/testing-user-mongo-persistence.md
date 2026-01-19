# Testing Plan: User MongoDB Persistence + Telegram Linkage

## Overview
This document outlines comprehensive testing steps to verify:
1. ✅ Users are persisted in MongoDB (already confirmed)
2. Telegram linkage is stored correctly in `User.telegram` field
3. All existing functionality remains intact
4. Telegram integration works with the new persistence model

---

## Test 1: User Persistence Across Container Restart

### Steps:
1. **Create a new user** via UI/API:
   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser1", "password": "testpass123"}'
   ```

2. **Verify user exists in MongoDB**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'testuser1'}).toArray()"
   ```
   **Expected**: User document with `_id`, `username`, `password_hash`, `created_at`

3. **Restart core-api container**:
   ```bash
   docker-compose restart core-api
   ```

4. **Login with same credentials**:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser1", "password": "testpass123"}'
   ```
   **Expected**: `200 OK` with access token

5. **Verify user still exists in MongoDB**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'testuser1'}).toArray()"
   ```
   **Expected**: Same user document (not recreated)

### Success Criteria:
- ✅ User persists across container restarts
- ✅ Login works after restart
- ✅ User ID remains the same

---

## Test 2: Telegram Linkage Storage

### Steps:
1. **Login and get token**:
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser1", "password": "testpass123"}' | jq -r '.access_token')
   ```

2. **Start Telegram linking flow**:
   ```bash
   curl -X POST http://localhost:8000/telegram/link/start \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json"
   ```
   **Expected**: `200 OK` with `code` and `expires_in_seconds`

3. **Send verification code to Telegram bot** (manually via Telegram app)

4. **Check Telegram status**:
   ```bash
   curl -X GET http://localhost:8000/telegram/status \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: `200 OK` with `linked: true`, `telegram_username`, `notifications_enabled: false`

5. **Verify MongoDB document structure**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'testuser1'}).pretty()"
   ```
   **Expected**: User document with `telegram` field containing:
   ```json
   {
     "telegram": {
       "telegram_user_id": <number>,
       "telegram_chat_id": <number>,
       "telegram_username": "<username or null>",
       "notifications_enabled": false,
       "linked_at": ISODate("...")
     }
   }
   ```

### Success Criteria:
- ✅ `telegram` field is present in MongoDB document
- ✅ All Telegram fields are correctly stored
- ✅ `/telegram/status` returns correct data

---

## Test 3: Verification Flow End-to-End

### Steps:
1. **Login and get token** (use existing user or create new)

2. **Generate verification code**:
   ```bash
   RESPONSE=$(curl -s -X POST http://localhost:8000/telegram/link/start \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json")
   CODE=$(echo $RESPONSE | jq -r '.code')
   echo "Verification code: $CODE"
   ```

3. **Send code to Telegram bot** (manually via Telegram app)

4. **Verify bot responds** with success message: "✅ Account linked successfully!"

5. **Check status**:
   ```bash
   curl -X GET http://localhost:8000/telegram/status \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: `linked: true`

6. **Verify MongoDB**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'testuser1'}).pretty()"
   ```
   **Expected**: User has `telegram` field populated

7. **Test expired code** (wait 10+ minutes or manually expire):
   - Generate new code
   - Wait 10+ minutes
   - Send expired code to bot
   **Expected**: Bot responds with "Invalid or expired verification code"

### Success Criteria:
- ✅ Verification code generation works
- ✅ Code linking works via Telegram bot
- ✅ Expired codes are rejected
- ✅ MongoDB is updated correctly

---

## Summary Checklist

- [ ] Test 1: User Persistence ✅ (Already confirmed)
- [ ] Test 2: Telegram Linkage Storage
- [ ] Test 3: Verification Flow End-to-End
- [ ] Test 4: Telegram Status Endpoint
- [ ] Test 5: Unlink Flow
- [ ] Test 6: Notifications Toggle
- [ ] Test 7: Weekly Summaries Integration
- [ ] Test 8: Backward Compatibility - Task Operations
- [ ] Test 9: Webhook Processing with Linked Users
- [ ] Test 10: Data Integrity - MongoDB Document Structure
- [ ] Test 11: Multiple Users Isolation
- [ ] Test 12: Container Restart with Telegram Links

---

## Quick Test Commands Reference

```bash
# Check users in MongoDB
docker-compose exec mongodb mongosh taskgenius --eval "db.users.find().pretty()"

# Check Telegram links
docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({telegram: {\$exists: true}}).pretty()"

# Check verification codes
docker-compose exec mongodb mongosh taskgenius --eval "db.telegram_verification_codes.find().toArray()"

# Check weekly summaries tracking
docker-compose exec mongodb mongosh taskgenius --eval "db.telegram_weekly_summaries.find().toArray()"

# View core-api logs
docker-compose logs core-api --tail 100 --follow

# Restart core-api
docker-compose restart core-api
```

---

## Notes

- All tests assume `core-api` is running on `http://localhost:8000`
- Replace `$TOKEN` with actual JWT token from login
- Some tests require manual interaction with Telegram bot
- Weekly summary tests may require waiting for scheduler interval or manual triggering
