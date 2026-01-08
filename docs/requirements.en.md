# TASKGEMIUS — Project Requirements (English)

## 1. Overview
Build a Task Management Platform that enables users to manage tasks, deadlines, and progress, augmented by:
- AI-powered insights (stable, structured analytics)
- An integrated chatbot service (conversational command interface)

The project must preserve clean architecture principles, with strict separation of concerns and clear service boundaries.

## 2. Mandatory Runtime Topology (3 Containers)
The system must run as a single monorepo and include exactly three runtime containers:
1) **core-api** (Python FastAPI) — the only public backend entrypoint and system of record  
2) **chatbot-service** (Python FastAPI) — internal-only conversational interpretation layer  
3) **mongodb** — internal-only database, accessible only by core-api

### 2.1 Communication Rules (Non-negotiable)
- The Web Client communicates **only** with core-api.
- core-api communicates with chatbot-service via **internal HTTP** over the Docker network.
- core-api communicates with mongodb via the database driver.
- chatbot-service must **never** access mongodb directly.
- mongodb and chatbot-service must **not** be exposed publicly (no host port mapping).

## 3. Web Client (TypeScript + React)
The web client must provide:
- User authentication flows (register, login, logout)
- Task CRUD user interface (create, list, view, update, delete)
- Task filtering/sorting (minimum: by status and by deadline)
- Embedded Web Chat interface (chat widget) that interacts with core-api
- Views for AI outputs (weekly summary and recommendations)

## 4. Core API (FastAPI) — Responsibilities and Boundaries
core-api must provide:
- Authentication and authorization (simple username/password is sufficient)
- Task management domain and business rules
- Task CRUD endpoints and filtering endpoints
- Input validation across all endpoints
- Ownership enforcement (users can only access their own tasks)
- Orchestration of AI capabilities:
  - calling chatbot-service for conversational interpretation
  - generating AI Insights reports from validated task data
- External integrations:
  - Telegram notifications on task create/update/complete
  - weekly AI-generated summary delivery

### 4.1 System-of-Record Rule
All task mutations (create/update/delete/complete) must be executed by core-api only, after:
- Authentication and authorization checks
- Validation of inputs (including AI-produced structured outputs)
- Consistency checks (e.g., conflict/overlap detection policy)

## 5. MongoDB Requirements
MongoDB must store:
- Users
- Tasks
- AI-related metadata (classification results, confidence, tags, and/or cached reports if desired)

MongoDB access rules:
- Only core-api may read/write MongoDB.
- All queries must be user-scoped and optimized for common filters.

## 6. Task Data Model Requirements
A task must support at minimum:
- `title` (string, required)
- `description` (string, optional)
- `status` (enum, required)
- `priority` (enum, required; user/AI assigned)
- `category` (enum, optional; AI inferred)
- `deadline` (timestamp, optional)
- `created_at`, `updated_at` (timestamps)
- `estimate_bucket` (enum, optional; AI inferred)

### 6.1 Derived Urgency (Time-based) — Mandatory Concept
The system must define a **derived urgency level** computed from task `deadline` and current time:
- Urgency is **not** the same as user priority.
- Urgency is computed deterministically inside core-api and can be returned in responses.

A recommended urgency classification is:
- `NO_DEADLINE` (deadline missing)
- `OVERDUE` (deadline passed and task not DONE/CANCELED)
- `DUE_TODAY`
- `DUE_SOON` (within next 7 days)
- `NOT_SOON` (more than 7 days away)

core-api must be the authority for this computation.

## 7. External API Integrations
### 7.1 OpenAI API (AI Capabilities)
OpenAI must be integrated to:
- Analyze task descriptions and infer structured categorization (enum mapping)
- Estimate task complexity/time using stable buckets (enum mapping)
- Generate AI insights from historical task data
- Produce concise summaries derived strictly from validated task data

### 7.2 Telegram API
Telegram must be integrated to:
- Notify users when tasks are created, updated, or completed
- Deliver a weekly AI-generated summary of open and completed tasks

## 8. Chatbot Service (Additional Required Service)
### 8.1 Purpose
chatbot-service acts as a conversational interface for task management operations and insights.

### 8.2 Responsibilities
chatbot-service must:
- Accept natural language task-related messages
- Perform intent classification and entity extraction
- Produce a **structured action plan** (proposal) and a draft conversational reply
- Maintain per-session context if applicable (within its own scope)

### 8.3 Strict Boundaries
- No direct database access
- No direct task mutation
- No bypass of core-api authentication/authorization
- All execution and mutations must be performed by core-api

## 9. Chatbot SOP (Mandatory)
All chat flows must follow: **Interpret → Validate → Disambiguate → Execute**.
- Interpret: classify intent and extract entities (chatbot-service)
- Validate: core-api validates enums, formats, and required fields
- Disambiguate: if target task or required fields are unclear, ask one targeted question
- Execute: core-api executes mutation only when `ready=true`

Additional mandatory rules:
- Update/Delete must be unambiguous (exact target resolved)
- Delete must require explicit confirmation
- If potential duplicates/overlaps exist, core-api must return candidates and the chatbot must request user resolution

## 10. AI Insights Facade (Analytical Reporting)
The system must produce stable, structured insights derived from validated task data.
Weekly summary must include:
- Completed tasks in the last 7 days
- Open high-priority tasks
- Tasks due within the next 7 days
- Overdue tasks

Weekly summary must support:
- Automatic weekly publication
- On-demand generation via chat
Both modes must reuse the same structured report.

## 11. Security Requirements (Mandatory)
The system must implement:
- Input validation across all endpoints
- Secure secret handling via environment variables (no hardcoded keys)
- Rate limiting on sensitive endpoints (auth, chat)
- CORS restricted to the configured client origin
- Request logging and basic monitoring signals
- Internal services not exposed publicly (no host ports for mongodb/chatbot-service)

## 12. Dockerization and AWS Deployment (Mandatory)
- Provide Dockerfiles and docker-compose.yml for the 3 containers
- Ensure proper networking and service discovery (internal HTTP)
- Deploy on AWS EC2 or AWS Elastic Beanstalk
- Document deployment and environment configuration

## 13. Custom Feature (Mandatory)
Implement at least one additional feature that:
- Is relevant to task management/productivity/AI workflows
- Integrates cleanly with the existing architecture
- Does not introduce unrelated technologies

## 14. Testing and CI/CD (Mandatory)
- Automated tests for auth and task CRUD
- Tests for chatbot gating/disambiguation/confirmation rules
- Tests for weekly summary rules
- CI pipeline that runs tests and basic checks on push/PR
- README must include setup and test instructions
