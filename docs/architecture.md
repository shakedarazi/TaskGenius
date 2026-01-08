# TASKGEMIUS — Architecture

## 1. High-Level Topology (3 Containers)
- **Web Client (React)** communicates only with **core-api** (public).
- **core-api (FastAPI)**:
  - reads/writes **mongodb** (internal)
  - calls **chatbot-service** over internal HTTP (internal)
- **chatbot-service (FastAPI)** is internal-only and never accesses mongodb.

## 2. Communication Rules
- Client -> core-api: public HTTP
- core-api -> mongodb: DB driver connection
- core-api -> chatbot-service: internal HTTP over Docker network (service name routing)
- chatbot-service -> mongodb: forbidden
- Client -> chatbot-service: forbidden

## 3. Clean Architecture Boundaries (Facades)
### 3.1 System of Record: core-api
core-api owns:
- Authentication/authorization
- Task domain, validation, and persistence
- Derived fields (e.g., time-based urgency)
- Business rules and consistency checks
- Orchestration of AI and external integrations

### 3.2 Conversational Facade: chatbot-service
chatbot-service provides:
- Intent classification
- Entity extraction
- Structured action proposal (`ready`, `missing_fields`, `target_candidates`, etc.)
- Draft conversational replies
It does not persist tasks and does not execute mutations.

### 3.3 Analytical Facade: AI Insights (inside core-api)
AI Insights produces:
- Structured reports derived from validated task data (weekly summary, recommendations)
These reports are channel-independent and reused by Web/Chat/Telegram.

## 4. Internal HTTP (Definition)
Internal HTTP means service-to-service calls on the private Docker network using service DNS names, e.g.:
- `http://chatbot-service:<port>/...`
No public port exposure is allowed for internal services.

## 5. Non-Negotiable Constraints
- Only core-api can access MongoDB.
- All task mutations happen in core-api after validation and authorization.
- Chatbot outputs are non-authoritative proposals.
- MongoDB and chatbot-service are internal-only.
