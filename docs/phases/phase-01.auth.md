# Phase 1 Summary — Authentication & Authorization

## Phase Scope

### In Scope
Phase 1 establishes the authentication and authorization foundation for TASKGEMIUS. This includes:
- User registration and login flows
- JWT-based access token issuance and validation
- Protected route enforcement via FastAPI dependencies
- User-scoped request context for downstream use

### Out of Scope (Deferred)
- MongoDB persistence (Phase 2)
- Task CRUD operations (Phase 2)
- Chatbot service integration (Phase 4)
- AI Insights (Phase 3)
- Telegram notifications (Phase 5)
- Rate limiting and security hardening (Phase 6)
- Frontend/Web Client implementation

---

## What Was Implemented

### Authentication Flow
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create new user with username/password |
| `/auth/login` | POST | Authenticate and receive JWT access token |
| `/auth/me` | GET | Return current user info (protected) |

### JWT Handling
- Tokens issued on successful login containing user ID (`sub`), expiration (`exp`), and issued-at (`iat`) claims
- Token validation dependency (`get_current_user`) extracts and verifies JWT from `Authorization: Bearer <token>` header
- Configurable secret, algorithm, and expiration via environment variables

### Protected Routes
- `get_current_user` dependency enforces authentication
- Returns 401 Unauthorized for missing, invalid, or expired tokens
- Provides `CurrentUser` type alias for clean dependency injection

### Temporary Mechanisms
- **In-memory user repository**: Users stored in a Python dictionary during runtime
- Repository interface (`UserRepositoryInterface`) designed for Phase 2 MongoDB swap
- No persistence across restarts (acceptable for Phase 1 scope)

---

## Architectural Notes

### Alignment with docs/architecture.md
Phase 1 implements the **Authentication/Authorization** responsibility defined under the System of Record (core-api). Per the architecture:
- core-api owns authentication and authorization
- All protected operations will flow through JWT validation
- No MongoDB persistence yet (deferred to Phase 2)
- No chatbot-service involvement (deferred to Phase 4)

### System Boundaries
| Component | Phase 1 Status |
|-----------|----------------|
| core-api | Active — auth endpoints implemented |
| mongodb | Not used — in-memory store only |
| chatbot-service | Not involved |
| Web Client | Not involved |

---

## How to Run / Verify

### Required Services
For local development, only core-api needs to run. For Docker-based testing, all services can be started but only core-api is exercised.

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `dev-secret-key-change-in-production` | Secret for signing JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration in minutes |

### Run Commands

**Local (without Docker):**
```bash
cd services/core-api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Docker Compose:**
```bash
docker compose up --build -d
```

### Test Commands
```bash
cd services/core-api
pytest tests/ -v
```

Or run only auth tests:
```bash
pytest tests/test_auth.py -v
```

---

## Capabilities Added

After Phase 1, the system can:
- ✅ Register new users with username/password
- ✅ Authenticate users and issue JWT access tokens
- ✅ Validate JWT tokens on protected endpoints
- ✅ Reject requests with missing, invalid, or expired tokens
- ✅ Provide user context (`current_user`) to protected route handlers
- ✅ Hash passwords securely using bcrypt (no plaintext storage)

---

## Verification Gate

Phase 1 is complete when:

- [ ] All 20 tests pass (`pytest tests/ -v`)
- [ ] `POST /auth/register` creates user and returns 201
- [ ] `POST /auth/login` returns valid JWT for correct credentials
- [ ] `POST /auth/login` returns 401 for wrong password
- [ ] `GET /auth/me` returns user info with valid token
- [ ] `GET /auth/me` returns 401 without token
- [ ] `GET /auth/me` returns 401 with invalid token
- [ ] `GET /auth/me` returns 401 with expired token
- [ ] Password is stored as bcrypt hash (not plaintext)
- [ ] Docker container builds and runs healthy

---

## Git Commit

### Commit Title
```
feat(core-api): implement Phase 1 authentication & authorization
```

### Commit Body
```
- Add /auth/register, /auth/login, /auth/me endpoints
- Implement JWT issuance and validation with configurable settings
- Create get_current_user dependency for protected routes
- Add in-memory user repository with interface for Phase 2 swap
- Secure password hashing with bcrypt
- Add comprehensive pytest test suite (15 auth tests)
- Update requirements.txt with bcrypt, python-jose, pytest, httpx
```

### Example Commands
```bash
git add .
git commit -m "feat(core-api): implement Phase 1 authentication & authorization"
git push origin main
```

---

## Notes / Non-Goals

Phase 1 explicitly does **NOT** include:
- MongoDB integration or persistent user storage
- Task CRUD operations or task domain logic
- Chatbot service integration or conversational flows
- AI Insights or weekly summary generation
- Telegram notifications
- Frontend/Web Client implementation
- Rate limiting or advanced security hardening
- CORS restriction enforcement (defaults configured)
- User roles or permission levels beyond basic authentication
