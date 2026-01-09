# Phase 2 Summary — Task CRUD with MongoDB (CI-safe tests)

## Phase Objective

Phase 2 implements MongoDB-backed task persistence in core-api with full CRUD operations, ownership enforcement, and derived urgency computation. A key requirement is that all tests run without MongoDB, enabling CI pipelines to execute without database provisioning.

---

## Scope

### In Scope
- Task CRUD endpoints in core-api (POST, GET, PATCH, DELETE)
- MongoDB-backed repository for runtime persistence
- Ownership enforcement (users can only access their own tasks)
- Derived urgency computation from deadline and status
- CI-safe tests using in-memory repository

### Out of Scope
- AI Insights / analytics
- Chatbot integration
- Telegram integration
- Frontend / UI
- Any Phase 3+ features

---

## Implementation Overview

### MongoDB Integration
- MongoDB runs as an internal Docker service via `docker-compose.yml`
- No public port exposure — accessible only within the Docker network
- Connection managed via `MONGODB_URI` environment variable
- Database lifecycle (connect/disconnect) handled in FastAPI lifespan events

### Repository Abstraction
- `TaskRepositoryInterface` defines the contract for task data access
- `TaskRepository` — MongoDB implementation for runtime
- `InMemoryTaskRepository` — In-memory implementation for CI tests
- FastAPI dependency injection allows swapping implementations

### Ownership Enforcement
- All task queries are scoped by `owner_id` derived from JWT
- Users cannot read, update, or delete tasks belonging to other users
- Ownership is enforced at the repository query level

### Derived Urgency Classification
Urgency is computed deterministically from `deadline` and `status`:

| Urgency Level | Condition |
|---------------|-----------|
| `no_deadline` | Deadline is not set |
| `overdue` | Deadline passed AND status is not DONE/CANCELED |
| `due_today` | Deadline is today |
| `due_soon` | Deadline within next 7 days |
| `not_soon` | Deadline more than 7 days away |

### Architectural Constraint
**Only core-api accesses MongoDB.** No other service may read or write to the database.

---

## Runtime Setup (Local / Dev)

### Required Services
| Service | Description |
|---------|-------------|
| `mongodb` | Internal database (no host port) |
| `core-api` | Public backend on port 8000 |
| `chatbot-service` | Internal service (required by docker-compose) |

### Required Environment Variables
| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB connection string (e.g., `mongodb://mongodb:27017`) |
| `MONGODB_DATABASE` | Database name (e.g., `taskgenius`) |
| `JWT_SECRET_KEY` | Secret key for JWT signing |

### Commands

**Start the stack:**
```bash
docker compose up -d --build
```

**Verify containers:**
```bash
docker compose ps
```

**Health check:**
```bash
curl http://localhost:8000/health
```

**Stop the stack:**
```bash
docker compose down
```

---

## API Smoke Examples (Runtime)

### 1. Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpassword123"}'
```

### 2. Login and Get Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpassword123"}'
# Response: {"access_token": "<JWT>", "token_type": "bearer"}
```

### 3. Create Task
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Task", "priority": "high", "deadline": "2026-01-20T12:00:00Z"}'
```

### 4. List Tasks (with filter)
```bash
curl -X GET "http://localhost:8000/tasks?status=open" \
  -H "Authorization: Bearer <JWT>"
```

### 5. Update Task
```bash
curl -X PATCH http://localhost:8000/tasks/<task_id> \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

### 6. Delete Task
```bash
curl -X DELETE http://localhost:8000/tasks/<task_id> \
  -H "Authorization: Bearer <JWT>"
```

---

## Test Strategy (Critical)

### CI Reality
- **GitHub Actions does NOT provision MongoDB.**
- All tests must run without any database services.
- No `.env` file is required for tests.

### In-Memory Repository
- `InMemoryTaskRepository` implements the same interface as `TaskRepository`
- FastAPI's `dependency_overrides` swaps the repository in tests:
  ```python
  app.dependency_overrides[get_task_repository] = override_get_task_repository
  ```

### Deterministic Time Handling
- Urgency tests use frozen time fixtures
- `FrozenClock` class provides controllable datetime for testing
- Tests do not depend on system clock

### CI Command
```bash
cd services/core-api
pytest tests/ -v --tb=short
```

### Test Coverage
| Category | Tests |
|----------|-------|
| Task CRUD | Create, Read, Update, Delete |
| Ownership Isolation | User A cannot access User B's tasks |
| Urgency Computation | All 5 urgency levels verified |
| Authentication | JWT required for all task endpoints |

---

## Verification Gate (Phase Completion Criteria)

Phase 2 is considered complete only if:

- [ ] CI tests pass (`pytest tests/ -v --tb=short`) — 63 tests, no MongoDB
- [ ] Docker Compose stack starts successfully (`docker compose up -d --build`)
- [ ] All containers healthy (`docker compose ps`)
- [ ] Health endpoint returns 200 (`GET /health`)
- [ ] Manual CRUD smoke test succeeds against real MongoDB runtime

---

## Capabilities Added

- **Task CRUD Operations** — Create, read, update, delete tasks via REST API
- **MongoDB Persistence** — Tasks stored in MongoDB with async Motor driver
- **Ownership Enforcement** — Users isolated to their own tasks at query level
- **Derived Urgency** — Automatic urgency classification based on deadline
- **Filtering** — List tasks by status and deadline range
- **CI-Safe Testing** — Full test suite runs without database dependencies

---

## Git Commit

### Commit Title
```
feat(phase-2): implement Task CRUD with MongoDB and CI-safe tests
```

### Commit Body
```
- Add MongoDB connection lifecycle (Motor async driver)
- Implement Task model with all required fields
- Create TaskRepository (MongoDB) and InMemoryTaskRepository (tests)
- Add CRUD endpoints: POST/GET/PATCH/DELETE /tasks
- Enforce ownership isolation at query level
- Implement derived urgency computation from deadline
- Add filtering by status and deadline range
- Create 63 CI-safe tests using in-memory repository
- Update requirements.txt with motor and pymongo
```

### Commands
```bash
git status
git add -A
git commit -m "feat(phase-2): implement Task CRUD with MongoDB and CI-safe tests"
git push
```

---

## Notes / Constraints

### Architectural Rules
- **Only core-api accesses MongoDB** — No other service may connect to the database
- **MongoDB is internal-only** — No public port exposure in docker-compose
- **No analytics or chatbot logic** — These belong to Phase 3+

### Testing Rules
- Tests must never require MongoDB
- Tests must not depend on `.env` files
- All time-dependent tests must use frozen/controllable clocks

### Enum Immutability
- All enums (TaskStatus, TaskPriority, TaskCategory, EstimateBucket, UrgencyLevel) are derived from `shared/contracts/enums.json`
- Enums must not be modified
