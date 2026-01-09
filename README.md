# TASKGENIUS

Task management platform with AI-powered insights and an integrated chatbot service.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Browser                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  React Client (:5173)                    │    │
│  │                  packages/client                         │    │
│  └─────────────────────────────┬───────────────────────────┘    │
└────────────────────────────────┼────────────────────────────────┘
                                 │ HTTP REST
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Network                                │
│  ┌─────────────┐    ┌──────────────────┐    ┌────────────┐      │
│  │  core-api   │───▶│ chatbot-service  │    │  mongodb   │      │
│  │  (public)   │    │   (internal)     │    │ (internal) │      │
│  │  :8000      │    │   :8001          │    │  :27017    │      │
│  └──────┬──────┘    └──────────────────┘    └─────▲──────┘      │
│         │                                          │             │
│         └──────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for client development)
- Python 3.11+ (for backend development)

### Run Everything (Dev Mode)

```bash
# 1. Start MongoDB
docker compose up -d mongodb

# 2. Install root dependencies
npm install

# 3. Install client dependencies
npm run install:client

# 4. Start backend + frontend concurrently
npm run dev
```

This starts:
- **core-api**: http://localhost:8000
- **React Client**: http://localhost:5173

### Alternative: Run with Full Docker

```bash
# Build and start all services
docker compose up --build

# Health check
curl http://localhost:8000/health
```

## Project Structure

```
TaskGenius/
├── package.json            # Root workspace scripts
├── docker-compose.yml      # Container orchestration
├── docs/                   # Documentation
├── shared/contracts/       # Shared schemas and enums
├── packages/
│   └── client/             # React + TypeScript + Vite
│       ├── src/
│       │   ├── api/        # Typed HTTP client
│       │   ├── types/      # Shared DTOs
│       │   ├── pages/      # Route-level views
│       │   ├── components/ # Reusable UI
│       │   └── routes/     # Routing config
│       └── ...
└── services/
    ├── core-api/           # Primary backend (public)
    └── chatbot-service/    # Conversational layer (internal)
```

## Environment Variables

### Client (`packages/client/.env`)
| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_CORE_API_BASE_URL` | `http://localhost:8000` | Core API URL |

### Core API
| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed client origins |
| `MONGODB_URI` | `mongodb://mongodb:27017` | MongoDB connection |
| `CHATBOT_SERVICE_URL` | `http://chatbot-service:8001` | Internal chatbot URL |

## Development Commands

```bash
# Root level
npm run dev              # Start backend + client
npm run dev:backend      # Start core-api only
npm run dev:client       # Start React client only
npm run test:backend     # Run backend tests
npm run test:client      # Run client tests

# Client level (from packages/client)
npm run dev              # Start Vite dev server
npm run build            # Production build
npm run lint             # Run ESLint
npm run test             # Run Vitest
```

## Architecture Principles

1. **Client → core-api only**: React client communicates exclusively with core-api
2. **chatbot-service is advisory**: Provides intent/entity extraction, never executes mutations
3. **core-api is system of record**: All data mutations happen here after validation
4. **Internal services isolated**: MongoDB and chatbot-service have no public exposure

## Documentation

- [Requirements](docs/requirements.en.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Chatbot SOP](docs/chatbot_sop.md)
- [Weekly Insights Spec](docs/insights_weekly_summary_spec.md)
- [Sequence Flows](docs/sequence_flows.md)

## License


## run it 

Step-by-Step Instructions
1. Install Root Dependencies
cd c:\Users\shaked arazi\Desktop\Projects\TaskGenius
npm install

2. Install Client Dependencies
cd packages/client
npm install

3. Set Up Python Virtual Environment (for Backend)
cd services/core-api
python -m venv venv
Activate it:

Platform	Command
Windows (PowerShell)	.\venv\Scripts\Activate.ps1
Windows (CMD)	venv\Scripts\activate.bat

4. Install Python Dependencies (core-api directory)

pip install -r requirements.txt

5. Run the Application
Option A: Run Everything Together (from root)
npm run dev
This starts:

Backend (FastAPI) on http://localhost:8000
Frontend (Vite/React) on http://localhost:5173
MIT