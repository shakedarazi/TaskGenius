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

## Test 4: Telegram Status Endpoint

### Steps:
1. **Test unlinked user**:
   ```bash
   # Create new user without Telegram link
   curl -X GET http://localhost:8000/telegram/status \
     -H "Authorization: Bearer $TOKEN_NEW_USER"
   ```
   **Expected**: `{"linked": false, "telegram_username": null, "notifications_enabled": false}`

2. **Test linked user** (after Test 3):
   ```bash
   curl -X GET http://localhost:8000/telegram/status \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: `{"linked": true, "telegram_username": "...", "notifications_enabled": false}`

### Success Criteria:
- ✅ Unlinked users return `linked: false`
- ✅ Linked users return correct Telegram data

---

## Test 5: Unlink Flow

### Steps:
1. **Unlink Telegram account** (user must be linked first):
   ```bash
   curl -X POST http://localhost:8000/telegram/unlink \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json"
   ```
   **Expected**: `200 OK` with `{"unlinked": true}`

2. **Verify status**:
   ```bash
   curl -X GET http://localhost:8000/telegram/status \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: `{"linked": false, ...}`

3. **Verify MongoDB**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'testuser1'}).pretty()"
   ```
   **Expected**: User document **without** `telegram` field (or `telegram: null`)

4. **Test bot message after unlink**:
   - Send message to Telegram bot
   **Expected**: Bot responds with message about needing to link account

### Success Criteria:
- ✅ Unlink removes `telegram` field from MongoDB
- ✅ Status endpoint reflects unlinked state
- ✅ Bot no longer recognizes user

---

## Test 6: Notifications Toggle

### Steps:
1. **Enable notifications** (user must be linked first):
   ```bash
   curl -X PATCH http://localhost:8000/telegram/notifications \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"enabled": true}'
   ```
   **Expected**: `200 OK` with `{"linked": true, "notifications_enabled": true}`

2. **Verify MongoDB**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'testuser1'}).pretty()"
   ```
   **Expected**: `telegram.notifications_enabled: true`

3. **Disable notifications**:
   ```bash
   curl -X PATCH http://localhost:8000/telegram/notifications \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"enabled": false}'
   ```
   **Expected**: `200 OK` with `{"linked": true, "notifications_enabled": false}`

4. **Verify MongoDB**:
   **Expected**: `telegram.notifications_enabled: false`

5. **Test without Telegram link**:
   ```bash
   # Use unlinked user
   curl -X PATCH http://localhost:8000/telegram/notifications \
     -H "Authorization: Bearer $TOKEN_UNLINKED" \
     -H "Content-Type: application/json" \
     -d '{"enabled": true}'
   ```
   **Expected**: `400 Bad Request` with error message

### Success Criteria:
- ✅ Notifications can be enabled/disabled
- ✅ MongoDB is updated correctly
- ✅ Unlinked users cannot toggle notifications

---

## Test 7: Weekly Summaries Integration

### Steps:
1. **Link Telegram account** (from Test 3)

2. **Enable notifications** (from Test 6)

3. **Create some tasks** via UI/API:
   ```bash
   curl -X POST http://localhost:8000/tasks \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Test Task 1",
       "status": "todo",
       "priority": "high"
     }'
   ```

4. **Check scheduler logs**:
   ```bash
   docker-compose logs core-api | grep -i "weekly\|summary"
   ```
   **Expected**: Logs showing scheduler running

5. **Manually trigger weekly summary** (if scheduler interval is too long):
   - Check `TELEGRAM_WEEKLY_SUMMARY_INTERVAL_SECONDS` in config
   - Or wait for scheduled run
   - Or manually call the service (requires code modification)

6. **Verify Telegram message received** (manually check Telegram app)

7. **Check MongoDB for summary tracking**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.telegram_weekly_summaries.find().toArray()"
   ```
   **Expected**: Document with `user_id`, `week_start`, `sent_at`

### Success Criteria:
- ✅ Scheduler reads from `User.telegram`
- ✅ Weekly summaries are sent to users with `notifications_enabled: true`
- ✅ Idempotency prevents duplicate sends

---

## Test 8: Backward Compatibility - Task Operations

### Steps:
1. **Create task**:
   ```bash
   curl -X POST http://localhost:8000/tasks \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Test Task",
       "status": "todo",
       "priority": "high"
     }'
   ```
   **Expected**: `201 Created` with task data

2. **List tasks**:
   ```bash
   curl -X GET http://localhost:8000/tasks \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: `200 OK` with task list

3. **Update task**:
   ```bash
   curl -X PATCH http://localhost:8000/tasks/<task_id> \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Updated Task"}'
   ```
   **Expected**: `200 OK` with updated task

4. **Delete task**:
   ```bash
   curl -X DELETE http://localhost:8000/tasks/<task_id> \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: `200 OK`

5. **Verify tasks in MongoDB**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.tasks.find().toArray()"
   ```
   **Expected**: Tasks are stored correctly

### Success Criteria:
- ✅ All task operations work as before
- ✅ No errors related to user persistence
- ✅ Tasks are correctly associated with user IDs

---

## Test 9: Webhook Processing with Linked Users

### Steps:
1. **Link Telegram account** (from Test 3)

2. **Send message to Telegram bot**:
   - Open Telegram app
   - Send message: "Create a task to test integration"

3. **Check core-api logs**:
   ```bash
   docker-compose logs core-api --tail 50
   ```
   **Expected**: Logs showing webhook processing

4. **Verify bot responds** (check Telegram app)

5. **Verify task was created** (if message was interpreted as task creation):
   ```bash
   curl -X GET http://localhost:8000/tasks \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: New task in list

6. **Test with unlinked user**:
   - Create new user without Telegram link
   - Try to send message to bot from different Telegram account
   **Expected**: Bot responds with message about needing to link account

### Success Criteria:
- ✅ Linked users can interact with bot
- ✅ Bot correctly maps Telegram user to application user
- ✅ Unlinked users receive helpful message

---

## Test 10: Data Integrity - MongoDB Document Structure

### Steps:
1. **Create user with Telegram link** (from Test 3)

2. **Query MongoDB directly**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find().pretty()"
   ```

3. **Verify document structure matches User model**:
   - `_id`: string (UUID)
   - `username`: string
   - `password_hash`: string
   - `created_at`: ISODate
   - `telegram`: object (if linked) with:
     - `telegram_user_id`: number
     - `telegram_chat_id`: number
     - `telegram_username`: string or null
     - `notifications_enabled`: boolean
     - `linked_at`: ISODate

4. **Test User.from_dict() round-trip**:
   - Query user from MongoDB
   - Verify `User.from_dict()` correctly parses all fields
   - Verify `User.to_dict()` produces same structure

### Success Criteria:
- ✅ MongoDB document structure matches User model
- ✅ Serialization/deserialization works correctly
- ✅ All fields are preserved

---

## Test 11: Multiple Users Isolation

### Steps:
1. **Create User A** and link Telegram account A

2. **Create User B** and link Telegram account B

3. **Verify User A's data**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'userA'}).pretty()"
   ```
   **Expected**: Only User A's data, with correct Telegram link

4. **Verify User B's data**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'userB'}).pretty()"
   ```
   **Expected**: Only User B's data, with correct Telegram link

5. **Test cross-user access** (should fail):
   ```bash
   # Try to access User B's tasks with User A's token
   curl -X GET http://localhost:8000/tasks \
     -H "Authorization: Bearer $TOKEN_USER_A"
   ```
   **Expected**: Only User A's tasks (ownership isolation)

### Success Criteria:
- ✅ Users are isolated
- ✅ Telegram links are user-specific
- ✅ No data leakage between users

---

## Test 12: Container Restart with Telegram Links

### Steps:
1. **Create user and link Telegram** (from Test 3)

2. **Verify MongoDB has telegram field**:
   ```bash
   docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'testuser1'}).pretty()"
   ```

3. **Restart core-api**:
   ```bash
   docker-compose restart core-api
   ```

4. **Login and check Telegram status**:
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser1", "password": "testpass123"}' | jq -r '.access_token')
   
   curl -X GET http://localhost:8000/telegram/status \
     -H "Authorization: Bearer $TOKEN"
   ```
   **Expected**: `{"linked": true, ...}` (Telegram link persists!)

5. **Send message to Telegram bot**:
   **Expected**: Bot recognizes user and responds

### Success Criteria:
- ✅ Telegram links persist across container restarts
- ✅ Status endpoint returns correct data after restart
- ✅ Bot recognizes linked users after restart

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
