# How to Run TASKGENIUS Locally

## What "Full System" Means Here

The full system consists of:
- **core-api**: Primary backend service (FastAPI, port 8000)
- **chatbot-service**: Internal conversational service (FastAPI, port 8001, internal only)
- **mongodb**: Database (MongoDB 7.0, port 27017, internal only)
- **client**: React frontend (optional, runs separately via Vite dev server on port 5173)

All backend services are orchestrated via `docker-compose.yml`. The frontend client is not included in docker-compose and must be run separately.

## Prerequisites

- **Docker** and **Docker Compose** (for backend services)
- **Node.js** and **npm** (for frontend client, if running)
- **Python 3.11+** (optional, for running services without Docker)

Versions: As required by Docker Compose and the service Dockerfiles (Python 3.11-slim base images).

## Environment Setup

### Environment Variables

The system uses environment variables with defaults suitable for local development. No `.env` file is required for basic operation.

**core-api environment variables** (from `docker-compose.yml` and `app/config.py`):
- `DEBUG=false` (default: false)
- `MONGODB_URI=mongodb://mongodb:27017` (default: mongodb://mongodb:27017)
- `MONGODB_DATABASE=taskgenius` (default: taskgenius)
- `CHATBOT_SERVICE_URL=http://chatbot-service:8001` (default: http://chatbot-service:8001)
- `TELEGRAM_BOT_TOKEN` (optional, defaults to None)
- `LOG_LEVEL=INFO` (default: INFO)
- `CORS_ORIGINS` (default: http://localhost:5173,http://localhost:3000)
- `JWT_SECRET_KEY` (default: "dev-secret-key-change-in-production" - warning in production)
- `JWT_ALGORITHM=HS256` (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30` (default: 30)

**chatbot-service environment variables**:
- `DEBUG=false` (default: false)
- `CORE_API_URL=http://core-api:8000` (default: http://core-api:8000)
- `LOG_LEVEL=INFO` (default: INFO)

**Required to run**: All variables have defaults; no configuration required for local development.

**Optional**: `TELEGRAM_BOT_TOKEN` (only needed for Telegram webhook functionality).

## Run with Docker Compose (Primary Method)

### Step 1: Build and Start Services

From repository root:

```bash
docker compose up -d --build
```

This builds images for `core-api` and `chatbot-service`, pulls `mongo:7.0`, and starts all services.

### Step 2: Verify Services Are Running

```bash
docker compose ps
```

Expected output: All three services (core-api, chatbot-service, mongodb) should show status "Up" and "healthy".

### Step 3: Verify Health Endpoints

**core-api health:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","service":"TASKGENIUS Core API","version":"0.1.0"}
```

**chatbot-service health** (from within Docker network):
```bash
docker exec taskgenius-chatbot-service python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/health').read().decode())"
```

Expected response:
```json
{"status":"healthy","service":"TASKGENIUS Chatbot Service","version":"0.1.0"}
```

### Step 4: Access API Documentation

If `DEBUG=true` (not set in docker-compose by default):
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Running Frontend Client (Optional)

The React frontend is not included in docker-compose. To run it:

```bash
cd packages/client
npm install
npm run dev
```

Frontend will be available at http://localhost:5173 (default Vite port).

## Run Without Docker (Secondary, Optional)

### core-api

```bash
cd services/core-api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Requirements:**
- MongoDB must be running (either via Docker or local installation)
- Set `MONGODB_URI` environment variable if not using default
- `chatbot-service` must be accessible at `CHATBOT_SERVICE_URL`

### chatbot-service

```bash
cd services/chatbot-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Requirements:**
- No external dependencies (read-only service)
- Accessible from core-api via network

## Test Commands (Local, Mirrors CI)

### core-api Tests

From `services/core-api`:

```bash
pytest tests/ -v --tb=short
```

**Test structure:**
- `tests/test_auth.py`: Authentication and JWT tests
- `tests/test_tasks.py`: Task CRUD and ownership isolation tests
- `tests/test_insights.py`: Weekly insights summary tests
- `tests/test_chat.py`: Chat endpoint and chatbot-service integration tests
- `tests/test_telegram.py`: Telegram webhook and adapter tests
- `tests/test_urgency.py`: Urgency computation tests
- `tests/test_health.py`: Health endpoint tests

**CI-safety:** All tests use in-memory repositories and mocked HTTP calls; no MongoDB or network access required.

### chatbot-service Tests

From `services/chatbot-service`:

```bash
pytest tests/ -v --tb=short
```

**Test structure:**
- `tests/test_health.py`: Health endpoint tests
- `tests/test_interpret.py`: Intent classification and response generation tests

**CI-safety:** All tests are pure unit tests; no external dependencies.

## Common Failures & Fixes

### Port Conflicts

**Symptom:** `Error: bind: address already in use` or `port is already allocated`

**Fix:**
- Check if port 8000 is in use: `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (Linux/Mac)
- Stop conflicting service or change port in `docker-compose.yml`
- For core-api, change `ports: - "8000:8000"` to another port (e.g., `"8002:8000"`)

### Database Connection Errors

**Symptom:** `RuntimeError: Database not connected. Call connect() first.`

**Fix:**
- Verify MongoDB container is running: `docker compose ps`
- Check MongoDB health: `docker logs taskgenius-mongodb`
- Ensure `MONGODB_URI` matches docker-compose service name: `mongodb://mongodb:27017`
- Wait for MongoDB to become healthy (start_period: 20s)

### Missing Environment Variables

**Symptom:** Application starts but behaves unexpectedly

**Fix:**
- All required variables have defaults; check `app/config.py` for defaults
- For production, set `JWT_SECRET_KEY` to a strong secret (min 32 chars)
- For production, set `CORS_ORIGINS` to specific origins (not wildcard)

### Auth Failures

**Symptom:** `401 Unauthorized` on protected endpoints

**Fix:**
- Register user first: `POST /auth/register` with username/password
- Login to get token: `POST /auth/login`
- Include token in header: `Authorization: Bearer <token>`
- Check token expiration (default: 30 minutes)

### Chatbot-Service Unreachable

**Symptom:** Chat endpoint returns fallback message or timeout

**Fix:**
- Verify chatbot-service is running: `docker compose ps`
- Check chatbot-service health: `docker logs taskgenius-chatbot-service`
- Verify `CHATBOT_SERVICE_URL` in core-api matches service name: `http://chatbot-service:8001`
- Check Docker network: `docker network inspect taskgenius-network`

### Telegram Webhook Errors

**Symptom:** Telegram webhook returns 200 but no response sent

**Fix:**
- `TELEGRAM_BOT_TOKEN` is optional; webhook accepts payloads but won't send responses without token
- Check user mapping: Telegram user must be linked to application user (currently in-memory)
- Verify Telegram adapter logs: `docker logs taskgenius-core-api`
