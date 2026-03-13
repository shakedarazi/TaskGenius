# TaskGenius
### 🚀 Secure AI-Assisted Task Management by Architectural Design

TaskGenius is a task management platform built around one strict rule:

> 🧠 **The AI component is structurally incapable of mutating user data.**

Instead of trying to make an LLM “safe enough” to act, TaskGenius removes that capability entirely.

The AI generates **suggestions only**. All real state changes are executed exclusively through validated backend APIs under explicit authentication, authorization, and ownership checks.

This project explores how **hard trust boundaries**, **capability separation**, and **container-level isolation** can make AI-assisted systems safer without relying on prompt discipline or model behavior.

---

## ❓ Why this project exists

Most AI-integrated applications eventually let models do one or more of the following:

- 🛠 call tools
- ⚙️ execute commands
- 🗄️ modify databases directly
- ⏱ trigger automations or workflows

That often creates fragile systems where safety depends on:

- 🧩 prompt correctness
- 🤖 model alignment
- 🙏 hoping the AI behaves as intended

TaskGenius explores a different approach:

> 🔒 **Instead of making AI safe enough to act, remove its ability to act entirely.**

The AI may recommend tasks, summarize tasks, or generate weekly insights — but it cannot persist, mutate, schedule, or notify on its own.

---

## ✨ Why TaskGenius is different

TaskGenius is not just a task app with an LLM attached to it.

It is designed around a stricter security model:

- 🧠 the AI is **inference-only**
- ✍️ all writes go through a **single mutation boundary**
- 🔐 authentication and authorization are centralized
- 🐳 trust boundaries are enforced at the **container and network level**
- 👤 human approval is required before persistence

This means safety comes from **architecture**, not from asking the model nicely.

---

## 🧱 Core architectural idea

Inference, mutation, and automation are separated at the architectural level.

- 🧠 **AI performs inference only** — task suggestions and summaries
- 🧾 **APIs perform mutations and scheduling** — validated task CRUD and automation triggers
- 🐳 **Infrastructure enforces isolation** — services have minimal privileges and constrained network access

Each responsibility is isolated in its own service with a deliberately narrow capability surface.

---

## 🏗 High-level architecture

### Main components

- 💻 **Client** — React + TypeScript (Vite)
- 🌐 **core-api** — the only public backend ingress
- 🤖 **chatbot-service** — internal AI suggestion service
- ⏱️ **scheduler / automation layer** — internal reminder and summary workflows
- 🗄️ **MongoDB** — internal data store, reachable only by `core-api`

### Service responsibilities

#### 🌐 `core-api` (public, single ingress)

- JWT authentication and authorization
- all task CRUD operations
- validation and ownership enforcement
- orchestration of AI and automation APIs
- single CORS enforcement boundary

#### 🤖 `chatbot-service` (internal)

- generates task suggestions only
- stateless by design
- no database access
- no exposed public ports
- no mutation capabilities

#### ⏱️ Scheduler / automation layer (internal)

- time-based task reminders
- weekly summaries or AI-generated insights
- Telegram notification orchestration through explicit backend paths

#### 🗄️ MongoDB (internal)

- accessible only by `core-api`
- never directly exposed to AI or automation services

### Network model

All services communicate over a **private Docker network**, but only one service is exposed externally.

---

## 🔐 Safety model and trust boundaries

TaskGenius enforces safety through architecture, not through AI behavior, prompt wording, or runtime optimism.

### 🚪 Single ingress, multiple isolated services

Although the system is composed of multiple containers, all external traffic enters through one controlled gateway:

- only `core-api` exposes a public port
- the frontend communicates exclusively with `core-api`
- AI, scheduler, and database services are not reachable from outside
- CORS is enforced at one boundary

This guarantees:

- 🔑 one authentication surface
- 🛂 one authorization surface
- 🌍 one CORS policy
- ✍️ one mutation entry point

Externally, the system behaves as a single logical backend, even though it is internally modular.

### 🧠 AI safety by capability removal

The AI service is not “trusted to behave.”

It is structurally incapable of acting.

It has:

- ❌ no database credentials
- ❌ no access to mutation APIs
- ❌ no ability to trigger schedulers or automations
- ❌ no exposed public ports
- ❌ no role in authentication or authorization

Even if the AI returns malicious output or is fully compromised, there is **no direct execution path** from AI output to persistent mutation.

### ✍️ Single point of mutation

All state changes flow through exactly one service:

`core-api` is the only service allowed to:

- create tasks
- update tasks
- delete tasks
- trigger scheduled jobs
- send Telegram notifications

Every mutation is:

- 🔐 authenticated via JWT
- 🛂 authorized through ownership checks
- ✅ validated through schema enforcement

There are no hidden write paths, side channels, or background shortcuts.

---

## 🔄 Example execution flow

A typical end-to-end flow looks like this:

1. 👤 The user describes a goal in natural language
2. 🌐 `core-api` requests suggestions from `chatbot-service`
3. 🤖 The AI returns structured task suggestions only
4. 👤 The user explicitly selects which suggested tasks to create
5. 🌐 `core-api` validates, authorizes, and persists the selected tasks
6. ⏱️ The scheduler later triggers reminders or summaries
7. 📬 Telegram notifications are sent through a dedicated backend automation path

### Key point

The AI is never part of the mutation path.

It may influence **what is suggested**, but never **what is executed**.

---

## 🐳 Docker as a security primitive

Docker is not used only for deployment convenience.

In TaskGenius, it acts as an architectural control boundary.

It enforces:

- 🔓 only `core-api` exposes a public port
- 🔒 internal services expose no public ports
- 🧱 minimal privilege per container
- 🌐 network-level trust boundaries between services

This makes isolation enforceable at runtime rather than merely documented at the code level.

---

## 🔥 What makes this project interesting

TaskGenius is interesting because it treats **trust boundaries as a product feature** and **architecture as a safety mechanism**.

It combines several strong system-design ideas in one project:

- 🧠 inference-only AI integration
- ✍️ single validated mutation boundary
- 🐳 container-enforced trust isolation
- 👤 human-in-the-loop persistence
- 🔐 centralized auth, authz, and validation
- ⏱ separated automation layer with no AI write authority

This makes it a stronger example of **safe AI-assisted systems design** than a typical task app with an LLM wrapper.

---

## 🧠 Engineering highlights

- ✅ AI service is structurally **incapable of mutating state**
- ✅ `core-api` is the **sole write authority**
- ✅ container/network layout enforces service trust boundaries
- ✅ authentication, authorization, and ownership checks are centralized
- ✅ automation is separated from AI inference capabilities
- ✅ deterministic backend behavior remains intact even with AI suggestions in the loop
- ✅ human approval is required before persistence

---

## 🎯 What this project demonstrates

TaskGenius demonstrates:

- 🏛️ security by architecture, not by prompt engineering
- 🧩 strict separation between inference, mutation, and automation
- 🔐 safe AI integration patterns for real applications
- 🐳 container-level trust enforcement
- 🔁 predictable backend behavior under explicit write controls
- 👤 human-in-the-loop execution in AI-assisted workflows

---

## ⚖️ Trade-offs and limitations

TaskGenius intentionally gives up some convenience in exchange for stronger safety guarantees.

### Current trade-offs

- 👤 more user involvement — the AI does not act autonomously
- 🚫 no AI-triggered mutations or scheduling
- 🧾 more backend mediation between suggestion and persistence
- ⚙️ less convenience than fully agentic systems

### Why these trade-offs are acceptable

They deliberately favor:

- 🔐 safety
- 📐 predictability
- 🔎 debuggability
- 🧱 trust-boundary clarity

over maximum automation.

---

## 🔮 Potential extensions

- 🧑‍💼 role-based suggestion policies
- 🤖 multi-agent suggestion ensembles that remain inference-only
- 🧾 event sourcing for task mutations
- 🌍 distributed scheduling via message brokers
- 📊 policy-driven notification routing
- 🛡 richer trust-boundary observability and audit trails

---

## 🚀 Getting started

### Prerequisites

- 🐳 Docker and Docker Compose
- Node.js 20+ (for local client development)
- Python 3.11+ (for local backend development)

### Quick start with Docker

#### 1. Clone the repository

```bash
git clone https://github.com/your-username/TaskGenius.git
cd TaskGenius
```

#### 2. Start all services

```bash
docker compose up --build
```

#### 3. Verify health

```bash
curl http://localhost:8000/health
```

#### 4. Run the client in development mode

```bash
cd packages/client
npm install
npm run dev
```

Access the application at:

```text
http://localhost:5173
```

---

## 🔧 Environment variables

Create a `.env` file in the project root for optional integrations.

### OpenAI integration (optional)
If not set, the system can fall back to template-based behavior.

```env
USE_LLM=true
OPENAI_API_KEY=sk-...
```

### Telegram integration (optional)

```env
TELEGRAM_BOT_TOKEN=your-bot-token
```

---

## 👥 Intended audience

This project is intended as:

- 💼 a portfolio showcase of architectural decision-making
- 📐 a reference design for safe AI-assisted systems
- 🎤 a discussion artifact for backend, platform, and R&D interviews

---

## 🧠 Key takeaway

> The safest AI system is one that is incapable of acting by design.

TaskGenius shows that enforcing strict architectural constraints — from APIs down to container boundaries — can eliminate entire classes of failure and security risk.

---

## ✨ Credits

Designed and implemented by **Shaked Arazi**.

TaskGenius was built with a strong emphasis on trust boundaries, backend mediation, and architecture-enforced AI safety.

