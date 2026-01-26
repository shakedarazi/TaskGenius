# 🚀 TaskGenius

A task management platform built around a strict architectural rule:

> 🧠 **The AI component is structurally incapable of mutating user data.**

TaskGenius demonstrates how enforcing **hard trust boundaries**, **capability separation**,
and **container-level isolation** enables safe AI-assisted systems —  
without relying on prompt discipline or model behavior.

---

## ❓ Why This Project Exists

Most AI-integrated applications allow models to:

- 🛠️ Call tools
- ⚙️ Execute commands
- 🗄️ Modify databases directly

This creates fragile systems where safety depends on:

- 🧩 Prompt correctness
- 🤖 Model alignment
- 🙏 Hoping the AI behaves as intended

TaskGenius explores a different approach:

> 🔒 **Instead of making AI safe enough to act, remove its ability to act entirely.**

The AI generates **suggestions only**.  
All data mutations are executed exclusively by **validated backend APIs**.

---

## 🧱 Core Architectural Idea

**Inference, mutation, and automation are separated at the architecture level.**

- 🧠 AI performs inference only (suggestions)
- 🧾 APIs perform mutations and scheduling
- 🐳 Infrastructure enforces isolation and trust boundaries

Each responsibility is isolated in its own service, with minimal privileges.

---

## 🏗️ High-Level Architecture

- 💻 **Client**: React + TypeScript (Vite)

- 🌐 **core-api** (public, single ingress):
  - Authentication & authorization (JWT)
  - All task CRUD operations
  - Validation and ownership enforcement
  - Orchestrates AI and automation APIs
  - Enforces CORS at a single boundary

- 🤖 **chatbot-service** (internal):
  - Generates task suggestions only
  - Stateless
  - No database access
  - No exposed ports

- ⏱️ **scheduler / automation layer** (internal):
  - Time-based task summaries and reminders
  - Weekly AI-generated insights
  - Telegram notification orchestration

- 🗄️ **MongoDB** (internal):
  - Accessible only by `core-api`

All services communicate over a **private Docker network**.

---

## 🔐 Safety Model & Trust Boundaries

TaskGenius enforces safety through **architecture**, not through AI behavior,
prompt discipline, or runtime checks.

### 🚪 Single Ingress, Multiple Isolated Services

Although the system is composed of multiple containers,  
**all external traffic enters through a single controlled gateway**:

- Only `core-api` exposes an external port
- The frontend communicates exclusively with `core-api`
- AI, scheduler, and database are **not reachable from the outside**
- CORS is enforced at **one boundary**

This guarantees:

- 🔑 One authentication surface
- 🛂 One authorization surface
- 🌍 One CORS policy
- ✍️ One mutation entry point

Externally, the system behaves as a **single logical backend**,  
despite being internally modular.

---

### 🧠 AI Safety by Capability Removal

The AI service is not “trusted to behave”.  
It is **incapable of acting**.

- ❌ No database credentials
- ❌ No access to mutation APIs
- ❌ No ability to trigger schedulers or automations
- ❌ No exposed ports
- ❌ No role in authentication or authorization

Even if the AI outputs malicious content or is fully compromised,  
there is **no execution path** from AI output to data mutation.

---

### ✍️ Single Point of Mutation

All state changes flow through one place:

- `core-api` is the **only service** allowed to:
  - Create tasks
  - Update tasks
  - Delete tasks
  - Trigger scheduled jobs
  - Send Telegram notifications

Every mutation is:

- 🔐 Authenticated (JWT)
- 🛂 Authorized (ownership checks)
- ✅ Validated (schema enforcement)

There are **no side channels**, background shortcuts, or hidden write paths.

---

## 🔄 Execution Flow (Simplified)

1. 👤 User describes a goal
2. 🌐 `core-api` requests suggestions from `chatbot-service`
3. 🤖 AI returns structured task suggestions
4. 👤 User explicitly selects which tasks to create
5. 🌐 `core-api` validates and persists tasks
6. ⏱️ Scheduler triggers time-based automations
7. 📬 Telegram notifications are sent via a dedicated API path

The AI is **never involved** in mutation or automation execution.

---

## 🐳 Docker as a Security Primitive

Docker is not used only for deployment convenience.

It is a **first-class architectural control**:

- 🔓 Only `core-api` exposes a public port
- 🔒 Internal services expose no ports
- 🧱 Containers have minimal privileges
- 🌐 Network-level isolation enforces trust boundaries

Even a compromised container cannot laterally move or escalate privileges.

---

## 🎯 What This Project Demonstrates

- 🏛️ **Security by architecture**, not by prompt engineering
- 🧩 **Clear separation** between inference, mutation, and automation
- 🔐 **Safe AI integration patterns**
- 🐳 **Container-level trust enforcement**
- 🔁 **Deterministic backend behavior**
- 👤 **Human-in-the-loop execution**

---

## ⚖️ Trade-offs & Limitations

- Higher user involvement (AI does not act autonomously)
- No AI-triggered mutations or scheduling
- Slightly less convenience compared to agent-based systems

These trade-offs intentionally favor **safety, predictability, and debuggability**
over maximum automation.

---

## 🔮 Potential Extensions

- 🧑‍💼 Role-based suggestion policies
- 🤖 Multi-agent suggestion ensembles (still inference-only)
- 🧾 Event sourcing for task mutations
- 🌍 Distributed scheduling via message brokers
- 📊 Policy-driven notification routing

---

## 🎓 Intended Audience

This project is intended as:

- 💼 A **portfolio showcase** of architectural decision-making
- 📐 A reference design for **safe AI-assisted systems**
- 🎤 A discussion artifact for backend, platform, and R&D interviews

---

## 🧠 Key Takeaway

> **The safest AI system is one that is incapable of acting by design.**

TaskGenius shows that enforcing strict architectural constraints —  
from APIs down to container boundaries —  
can eliminate entire classes of failure and security risks.



## 🚀 Getting Started
# Prerequisites 
🐳 Docker and Docker Compose 
Node.js 20+ (for local client development) 
Python 3.11+ (for local backend development) 


# Quick Start with Docker  
Clone the repository git clone https://github.com/your-username/TaskGenius.git
 cd TaskGenius
  # Start all services
   docker compose up --build
  # Verify health
  curl http://localhost:8000/health


  The React client must be built separately or run in development mode:
  cd packages/client
  npm install
  npm run dev 
     
  Access the application at http://localhost:5173.
  
   # Environment Variables
    Create a .env file in the project root for optional features:
  # OpenAI integration (optional - falls back to templates if not set)
      USE_LLM=true
      OPENAI_API_KEY=sk-... 
  # Telegram integration (optional)
      TELEGRAM_BOT_TOKEN=your-bot-token