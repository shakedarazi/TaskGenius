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

# TaskGenius

A task management platform with an AI-powered assistant that generates task suggestions without ever executing actions directly. The system enforces strict separation between AI inference and data mutation, ensuring that all changes to user data flow through controlled, validated API boundaries.

---

## 📋 Project Overview

TaskGenius addresses a fundamental problem in AI-integrated applications: how to leverage language models for productivity while maintaining complete control over what actions are actually performed.

Unlike typical "AI chatbot" implementations where the model can invoke tools, call APIs, or directly manipulate data, TaskGenius treats the AI as a **read-only suggestion engine**. The user describes what they need to accomplish, the AI generates structured task suggestions, and the user explicitly selects which suggestions to add. Every database write passes through the core API with full validation and authentication checks.

This architecture eliminates an entire class of risks associated with autonomous AI agents, including prompt injection attacks that attempt to trick the model into performing unintended actions.

---

## ✨ Key Features

| Feature                         | Description                                                                                           |
| ------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 🧠 **Suggestion-only AI**       | The chatbot service generates task recommendations but cannot create, modify, or delete any data      |
| 🧱 **Single point of mutation** | All database writes occur exclusively through the core API after schema validation and authentication |
| 🐳 **Microservice isolation**   | The AI service has no database credentials and no network path to the database                        |
| ⚙️ **Structured AI output**     | Model responses are parsed as strict JSON with fallback to deterministic templates on failure         |
| 🌐 **Multi-language support**   | Full Hebrew and English support with language-aware responses                                         |
| 📬 **Telegram integration**     | Optional notifications and weekly AI-generated summaries                                              |
| 🧪 **Comprehensive testing**    | Automated tests for both services run on every push via GitHub Actions                                |

---

## 🧱 System Architecture

```
                              Client
                     React + TypeScript (Vite)
                                |
                                | HTTPS (authenticated)
                                v
    +-----------------------------------------------------------+
    |                     Docker Network                         |
    |                                                            |
    |   +-----------------+         +-------------------+        |
    |   |    core-api     |-------->|  chatbot-service  |        |
    |   |  (public :8000) |         |  (internal :8001) |        |
    |   |                 |         |                   |        |
    |   | - Authentication|         | - Suggestion gen  |        |
    |   | - Authorization |         | - OpenAI calls    |        |
    |   | - All DB writes |         | - NO DB access    |        |
    |   | - Request valid.|         | - Stateless       |        |
    |   +--------+--------+         +-------------------+        |
    |            |                                               |
    |            | MongoDB protocol (internal only)              |
    |            v                                               |
    |   +-----------------+                                      |
    |   |     MongoDB     |                                      |
    |   | (internal:27017)|                                      |
    |   |  NO external    |                                      |
    |   |     port        |                                      |
    |   +-----------------+                                      |
    +-----------------------------------------------------------+
```

### Critical Architectural Invariants

1. **The chatbot-service cannot access MongoDB.** It has no connection string, no credentials, and no network route to the database container.

2. **The core-api is the single source of truth.** Every task creation, update, and deletion is validated and executed here.

3. **External traffic reaches only the core-api.** The chatbot-service and MongoDB expose no ports to the host machine.

---

## 🧠 AI Design Philosophy

### Always Suggestions, Never Actions

The chatbot-service receives a user message and returns a structured response containing:

- A two-sentence summary of what the user described
- Up to five task suggestions with title, priority, and optional metadata

It does not return commands. It does not indicate "ready to execute." It simply offers options.

### User-Controlled Execution

After receiving suggestions, the user explicitly selects which tasks to add. This selection triggers a standard task creation request to the core-api, completely bypassing the chatbot-service. The AI played its role (suggesting) and is no longer in the loop for the actual mutation.

### Structured Output with Deterministic Fallback

AI responses must conform to a strict JSON schema. If the model returns malformed output, the system falls back to deterministic, template-based suggestions rather than failing or passing through unparsed content.

### Why This Matters

Autonomous AI agents that can "take action" introduce risk surfaces that are difficult to fully secure:

- Prompt injection can trick the model into calling unintended functions
- Ambiguous user input can lead to destructive actions
- Model hallucinations can result in invalid operations

By making the AI purely advisory, these risks are structurally eliminated. Even if an attacker crafts a prompt that convinces the model to "output" a delete command, nothing happens because the chatbot-service has no mechanism to execute commands.

---

## 🔐 Security and Trust Boundaries

### Authentication and Authorization

- 🔐 **JWT-based authentication** - All core-api endpoints (except health checks) require a valid token
- 🔐 **Password hashing** - User credentials are hashed with bcrypt before storage
- 🔐 **Token expiration** - JWTs have configurable expiration with secure defaults
- 🔐 **Ownership enforcement** - Users can only access and modify their own tasks

### 🧱 Service Isolation

The chatbot-service is architecturally incapable of modifying data:

| Capability              |    core-api    |  chatbot-service   |
| :---------------------- | :------------: | :----------------: |
| Database connection     |      Yes       |         No         |
| Task CRUD operations    |      Yes       |         No         |
| User authentication     |      Yes       |         No         |
| External network access | Yes (outbound) | Yes (OpenAI only)  |
| Receives user requests  |      Yes       | No (internal only) |

Even if the chatbot-service were fully compromised, an attacker would gain access to a stateless container that can call OpenAI and respond to internal HTTP requests - nothing more.

### ⚙️ Request Validation

FastAPI with Pydantic provides automatic request validation:

- **Schema enforcement** - Invalid payloads are rejected before reaching business logic
- **Type coercion** - Strict typing prevents type confusion attacks
- **Field constraints** - Minimum/maximum lengths, enum validation, and format checks are declarative

### 🛡️ Threat Mitigations

🛡️ **Prompt Injection**

> AI cannot execute actions; output is parsed as data, not commands

🛡️ **Unauthorized Access**

> JWT authentication + ownership checks on every request

🛡️ **SQL/NoSQL Injection**

> Pydantic validation + MongoDB driver parameterization

🛡️ **Privilege Escalation**

> Chatbot-service has no privileges to escalate

🛡️ **Malformed AI Output**

> Strict JSON parsing with fallback to safe defaults

🛡️ **CSRF**

> Token-based auth (no cookies for API calls)

### Security by Architecture

The security model does not depend on prompt engineering or hoping the AI "behaves." The guarantees are structural:

- 🧱 The AI service physically cannot reach the database
- 🧱 The AI service has no credentials to any system
- 🧱 All mutations require authenticated requests to a separate service
- 🧱 The mutation service validates every field before writing

---

## ⚙️ Backend and Infrastructure

### 📦 core-api (FastAPI)

**Responsibilities:**

- User registration, login, and session management
- Task CRUD with ownership enforcement
- Weekly insights generation
- Telegram bot integration
- Orchestrating calls to chatbot-service
- All MongoDB operations

**Why FastAPI:**

- Native async support for I/O-bound workloads
- Automatic OpenAPI documentation
- Pydantic integration for request/response validation
- Dependency injection for clean separation of concerns
- High performance with minimal overhead

### 🧠 chatbot-service (FastAPI)

**Responsibilities:**

- Receiving messages from core-api (never from external clients)
- Generating task suggestions via OpenAI
- Returning structured JSON responses
- Falling back to deterministic templates when AI fails

The service is intentionally minimal (~150 lines of core logic). It maintains no state between requests.

### 🐳 Docker Configuration

```yaml
services:
  core-api:
    ports: ["8000:8000"] # Only public-facing service
    depends_on: [mongodb, chatbot-service]

  chatbot-service:
    # NO PORTS EXPOSED - internal only

  mongodb:
    # NO PORTS EXPOSED - internal only
```

Internal services communicate over a Docker bridge network. The host machine cannot directly reach the chatbot-service or MongoDB.

---

## 🔁 CI and Testing

### GitHub Actions Pipeline

Every push to `main` and every pull request triggers:

| Step                        | Description                                         |
| --------------------------- | --------------------------------------------------- |
| 🧪 **test-core-api**        | Runs pytest against all core-api tests              |
| 🧪 **test-chatbot-service** | Runs pytest against all chatbot-service tests       |
| 🐳 **build-docker**         | Builds both Docker images (runs only if tests pass) |
| ⚙️ **validate-compose**     | Validates docker-compose.yml syntax                 |

### 🧪 What Is Tested

- **Authentication flows** - Registration, login, token validation, expiration
- **Task operations** - CRUD with ownership enforcement, field validation
- **Chat integration** - Message handling, suggestion generation, fallback behavior
- **Edge cases** - Empty inputs, invalid schemas, malformed AI responses
- **Service boundaries** - Ensuring chatbot-service returns suggestions without side effects

### Why Testing Matters Here

AI-assisted features are notoriously difficult to test because model outputs vary. TaskGenius addresses this by:

- Mocking OpenAI calls in tests to ensure deterministic behavior
- Testing the fallback path independently
- Validating that AI output parsing correctly handles malformed responses
- Ensuring the suggestion-to-task flow works regardless of AI involvement

---

## 🚀 Getting Started

### Prerequisites

- 🐳 Docker and Docker Compose
- Node.js 20+ (for local client development)
- Python 3.11+ (for local backend development)

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/your-username/TaskGenius.git
cd TaskGenius

# Start all services
docker compose up --build

# Verify health
curl http://localhost:8000/health
```

The React client must be built separately or run in development mode:

```bash
cd packages/client
npm install
npm run dev
```

Access the application at `http://localhost:5173`.

### Environment Variables

Create a `.env` file in the project root for optional features:

```bash
# OpenAI integration (optional - falls back to templates if not set)
USE_LLM=true
OPENAI_API_KEY=sk-...

# Telegram integration (optional)
TELEGRAM_BOT_TOKEN=your-bot-token
```

---

## 📁 Project Structure

```
TaskGenius/
├── .github/workflows/ci.yml    # GitHub Actions pipeline
├── docker-compose.yml          # Container orchestration
├── packages/
│   └── client/                 # React + TypeScript frontend
│       ├── src/
│       │   ├── api/            # Typed HTTP client
│       │   ├── components/     # UI components
│       │   ├── pages/          # Route views
│       │   └── types/          # Shared type definitions
│       └── ...
└── services/
    ├── core-api/               # Primary backend (public)
    │   ├── app/
    │   │   ├── auth/           # Authentication module
    │   │   ├── tasks/          # Task management
    │   │   ├── chat/           # Chat orchestration
    │   │   ├── insights/       # Weekly summaries
    │   │   └── telegram/       # Bot integration
    │   └── tests/
    └── chatbot-service/        # AI suggestion service (internal)
        ├── app/
        │   ├── service.py      # Core suggestion logic
        │   ├── schemas.py      # Request/response models
        │   └── router.py       # HTTP endpoints
        └── tests/
```

---

## 💡 Why This Architecture

### The Problem with Autonomous AI

Many AI-integrated applications give the model direct access to tools, databases, or APIs. This creates a trust problem: you must trust that the model will never be tricked into misusing its capabilities.

Prompt injection research has shown this trust is misplaced. Models can be manipulated through carefully crafted inputs, and the attack surface grows with every capability you grant.

### The TaskGenius Approach

Instead of trying to make AI "safe enough" to trust with actions, TaskGenius removes the need for trust entirely:

- The AI cannot take actions because it has no mechanism to do so
- Suggestions are data, not commands
- The human remains in the loop for every mutation

This trades some convenience (no "just do it" commands) for complete control over what actually happens to user data.

### Trade-offs

| Aspect             | Traditional AI Agent                   | TaskGenius                          |
| ------------------ | -------------------------------------- | ----------------------------------- |
| **User effort**    | Lower (AI acts autonomously)           | Higher (user confirms actions)      |
| **Risk surface**   | Large (every capability is attackable) | Minimal (AI has no capabilities)    |
| **Predictability** | Variable (model-dependent)             | High (deterministic execution path) |
| **Debugging**      | Difficult (why did AI do X?)           | Straightforward (user chose X)      |

For a task management application where incorrect actions could delete important data or create confusion, the TaskGenius model prioritizes safety and predictability over automation.

---

## CREDITS

shaked arazi
