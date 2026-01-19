# Testing Progress - User MongoDB Persistence

## ✅ Completed Tests

### Test 1: User Persistence ✅
- **Status**: PASSED
- **Results**:
  - User exists in MongoDB: `ben` (ID: `2d4885f9-d5a7-4f97-9f47-c9fef64e05b6`)
  - User persists after container restart
  - Document structure: `_id`, `username`, `password_hash`, `created_at`
- **Notes**: User was created before migration and persists correctly

### Test 2: Telegram Linkage Storage ✅
- **Status**: PASSED
- **Results**:
  - `telegram` field exists in MongoDB document
  - All fields correctly stored: `telegram_user_id`, `telegram_chat_id`, `telegram_username`, `notifications_enabled`, `linked_at`
  - Structure matches `TelegramLink` model
- **Notes**: Telegram linkage successfully stored in User document

### Test 4: Telegram Status Endpoint ✅
- **Status**: PASSED
- **Results**:
  - `/telegram/status` returns correct data
  - UI displays: `linked: true`, `telegram_username: "neri2000"`, `notifications_enabled: true`
- **Notes**: Status endpoint works correctly

### Test 6: Notifications Toggle ✅
- **Status**: PASSED (after bug fix)
- **Results**:
  - Toggle notifications works correctly
  - **Bug Found & Fixed**: `set_notifications_enabled` was deleting `telegram` field when updating
  - **Fix Applied**: Added check to ensure `telegram` field exists before updating
  - Toggle now works without deleting the link
- **Notes**: Bug fixed in `services/core-api/app/auth/repository.py` and `services/core-api/app/telegram/router.py`

### Test 10: Data Integrity ✅
- **Status**: PASSED
- **Results**:
  - MongoDB document structure matches `User` model:
    - `_id`: string (UUID) ✅
    - `username`: string ✅
    - `password_hash`: string (bcrypt) ✅
    - `created_at`: ISODate ✅
    - `telegram`: object (when linked) ✅
  - `User.to_dict()` and `User.from_dict()` correctly handle serialization
- **Notes**: Structure is correct

### Test 12: Container Restart with Telegram Links ✅
- **Status**: PASSED
- **Results**:
  - Telegram linkage persists across container restart
  - User can login after restart
  - Telegram status remains correct after restart
- **Notes**: All data persists correctly in MongoDB

---

## 🔄 In Progress

### Test 8: Backward Compatibility - Task Operations
- **Status**: TESTING
- **Current State**: 41 tasks exist in MongoDB
- **Next Steps**: Verify task create/update/delete operations work correctly

---

## 📋 Pending Tests

- Test 3: Verification Flow End-to-End (can be skipped - already verified working)
- Test 5: Unlink Flow
- Test 7: Weekly Summaries Integration
- Test 9: Webhook Processing with Linked Users

---

## 🐛 Bugs Found & Fixed

### Bug 1: `set_notifications_enabled` deleting `telegram` field
- **Location**: `services/core-api/app/auth/repository.py`
- **Issue**: Method was updating `telegram.notifications_enabled` without checking if `telegram` field exists, causing MongoDB to delete the field
- **Fix**: Added check `{"telegram": {"$exists": True}}` in query filter
- **Status**: ✅ FIXED

---

## 🧪 Test Commands Reference

```bash
# Check users in MongoDB
docker-compose exec mongodb mongosh taskgenius --eval "db.users.find().pretty()"

# Check specific user
docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'ben'}).toArray()"

# Check Telegram links
docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({telegram: {$exists: true}}).toArray()"

# Check notifications status
docker-compose exec mongodb mongosh taskgenius --eval "db.users.find({username: 'ben'}).toArray()[0].telegram.notifications_enabled"

# View logs
docker-compose logs core-api --tail 50
```

---

## 📝 Notes

- All tests assume user `ben` exists with Telegram link
- Telegram bot must be configured and webhook set up
- Some tests require manual interaction with Telegram app
- **Critical Bug Fixed**: Notifications toggle no longer deletes Telegram link
