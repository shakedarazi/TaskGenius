# TASKGEMIUS — Roadmap (Phased Implementation)

## Phase 0 — Repository Baseline
- Monorepo structure finalized
- docs/ and shared/contracts/ are treated as immutable contracts
- docker-compose.yml and .env.example exist
- CI skeleton exists

## Phase 1 — Core API Authentication
- Register/login using username/password
- JWT issuance and validation dependency
- Protected routes enforce auth
- Tests: auth success/failure and protected route access

## Phase 2 — Core API + MongoDB: Task CRUD
- Task schema + validation + user ownership enforcement
- CRUD endpoints with filtering (status/deadline)
- Derived urgency field computed in core-api
- Tests: CRUD, isolation, deadline/overdue logic

## Phase 3 — AI Insights (Weekly Summary)
- Deterministic weekly summary report built from validated task data
- Same report structure for scheduled and on-demand usage
- Tests: report correctness on fixtures (mock AI where needed)

## Phase 4 — Chatbot Service Integration (SOP + Gating)
- chatbot-service internal-only contract established
- Core enforces: ready gating, disambiguation, delete confirmation
- Duplicate/overlap candidate flow: Core finds candidates, chatbot asks user to choose
- Tests: gating/disambiguation/confirmation flows

## Phase 5 — Telegram Integration + Scheduler
- Notifications on task create/update/complete
- Weekly scheduled summary delivery using the structured report
- Tests: Telegram client mocked; formatting derived from structured report

## Phase 6 — Security Hardening
- CORS restricted to client origin
- Rate limiting on auth/chat endpoints
- Secrets management validated
- Logging and basic monitoring signals

## Phase 7 — Docker + AWS Deployment
- Docker images built and run via compose
- mongodb/chatbot-service not exposed publicly
- Deploy to AWS EC2 or Elastic Beanstalk
- Document deployment steps and environment configuration

## Phase 8 — Custom Feature
- Implement one cohesive custom feature
- Tests included
- Demo video showcases the feature
