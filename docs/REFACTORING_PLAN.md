# TASKGENIUS Structural Refactoring — Technical Design Document

**Version:** 1.0  
**Status:** Pending Approval  
**Based on:** Structural Dependency Analysis (Leaves, Backbone, Circular Risks)

---

## 1. Final Architecture Definition

### 1.1 Standard Module Pattern

Every feature module must strictly contain these six files:

| File | Purpose | Mandatory |
|------|---------|-----------|
| `router.py` | HTTP route handlers only; delegates to service via Depends | Yes |
| `service.py` | Business logic; receives repository via constructor or parameters | Yes |
| `repository.py` | Data access; interfaces and MongoDB implementations | Yes |
| `schemas.py` | Pydantic request/response models | Yes |
| `models.py` | Domain entities (dataclasses), or re-exports from shared | Yes |
| `dependencies.py` | FastAPI dependency getters (get_X functions) | Yes |

**Exception:** Features that do not persist their own data (insights, chat) may have minimal `repository.py` and `models.py` that delegate or re-export from other features. The file must exist for structural consistency.

### 1.2 Current State vs. Target State by Feature

| Feature | router | service | repository | schemas | models | dependencies | Action |
|---------|--------|---------|------------|---------|--------|--------------|--------|
| auth | Yes | Yes | Yes | Yes | Yes | Yes | Remove duplicate `get_auth_service` from router; keep only in dependencies |
| tasks | Yes | Yes | Yes | Yes | Yes | **No** | Create dependencies.py; move `get_task_repository`, `get_task_service` from router |
| insights | Yes | Yes | **No** | Yes | **No** | **No** | Create repository.py (facade), models.py (minimal), dependencies.py; move `get_insights_service` from router |
| chat | Yes | Yes | **No** | Yes | **No** | **No** | Create repository.py (facade), models.py (minimal), dependencies.py |
| telegram | Yes | Yes | Yes | Yes | Yes | **No** | Create dependencies.py; move all getters from router |

### 1.3 Dependency Migration Strategy

**Explicit list of functions to migrate:**

| Function | Current Location | New Location |
|----------|------------------|--------------|
| `get_database` | `app/database.py` | `app/core/database.py` |
| `get_auth_service` | `app/auth/router.py` (duplicate) + `app/auth/dependencies.py` | `app/auth/dependencies.py` only (remove from router) |
| `get_current_user` | `app/auth/dependencies.py` | `app/auth/dependencies.py` (unchanged) |
| `CurrentUser` | `app/auth/dependencies.py` | `app/auth/dependencies.py` (unchanged) |
| `bearer_scheme` | `app/auth/dependencies.py` | `app/auth/dependencies.py` (unchanged) |
| `get_task_repository` | `app/tasks/router.py` | `app/tasks/dependencies.py` |
| `get_task_service` | `app/tasks/router.py` | `app/tasks/dependencies.py` |
| `get_insights_service` | `app/insights/router.py` | `app/insights/dependencies.py` |
| `get_telegram_service` | `app/telegram/router.py` | `app/telegram/dependencies.py` |
| `get_weekly_summary_service` | `app/telegram/router.py` | `app/telegram/dependencies.py` |
| `_get_user_repo` | `app/telegram/router.py` | `app/telegram/dependencies.py` (rename to `get_user_repo_for_telegram` or keep internal) |
| `_get_verification_repo` | `app/telegram/router.py` | `app/telegram/dependencies.py` |

**Import transition rule:** All consumers of `get_task_repository` must change from `from app.tasks.router import get_task_repository` to `from app.tasks.dependencies import get_task_repository`. Same for `get_telegram_service`, `get_insights_service`, etc.

---

## 2. Core Infrastructure Consolidation (Option B+)

### 2.1 Files to Move

| Source | Destination |
|--------|-------------|
| `app/config.py` | `app/core/config.py` |
| `app/database.py` | `app/core/database.py` |
| `app/security.py` | `app/core/security.py` |
| `app/tasks/enums.py` | `app/core/enums.py` |

### 2.2 Internal Reference Updates (within core/)

After moving files:

- `app/core/database.py` must import: `from app.core.config import settings`
- `app/core/security.py` must import: `from app.core.config import settings`

### 2.3 `app/core/__init__.py` Strategy

**Recommended: Re-export for cleaner imports.**

```python
"""
TASKGENIUS Core API - Foundation Layer

Provides config, database, security, and shared enums.
Import from app.core for consistent access.
"""

from app.core.config import settings, Settings
from app.core.database import database, get_database
from app.core.security import validate_security_config
from app.core.enums import (
    TaskStatus,
    TaskPriority,
    TaskCategory,
    EstimateBucket,
    UrgencyLevel,
)

__all__ = [
    "settings",
    "Settings",
    "database",
    "get_database",
    "validate_security_config",
    "TaskStatus",
    "TaskPriority",
    "TaskCategory",
    "EstimateBucket",
    "UrgencyLevel",
]
```

**Alternative (explicit imports only):** Do not re-export; force `from app.core.config import settings` everywhere. This avoids namespace pollution but increases verbosity.

**Decision:** Use re-exports for `settings`, `get_database`, `validate_security_config`, and enums. Domain code may use either `from app.core import settings` or `from app.core.config import settings`.

---

## 3. Import Refactoring Logic

### 3.1 Transition Rules for the AI Agent

| Rule | From | To |
|------|------|-----|
| R1 | `from app.config import settings` | `from app.core.config import settings` (or `from app.core import settings`) |
| R2 | `from app.database import get_database, database` | `from app.core.database import get_database, database` (or `from app.core import get_database, database`) |
| R3 | `from app.security import validate_security_config` | `from app.core.security import validate_security_config` (or `from app.core import validate_security_config`) |
| R4 | `from app.tasks.enums import X` | `from app.core.enums import X` |
| R5 | `from app.feature.router import get_X` | `from app.feature.dependencies import get_X` |
| R6 | `from app.tasks.router import get_task_repository` | `from app.tasks.dependencies import get_task_repository` |
| R7 | `from app.telegram.router import get_telegram_service` | `from app.telegram.dependencies import get_telegram_service` |

### 3.2 Absolute vs. Relative Imports

| Context | Rule | Example |
|---------|------|---------|
| Within same feature | Prefer relative for internal modules | `from .schemas import TaskResponse` |
| Cross-feature | Always absolute | `from app.tasks.dependencies import get_task_repository` |
| Core imports | Always absolute from app.core | `from app.core import get_database` |
| Avoid circularity | Higher layers never import from lower routers | insights never imports from chat; telegram may import from auth, tasks, insights |

**Circularity constraint:** Dependency direction must remain: `core -> auth -> tasks -> insights, chat -> telegram`. No feature may import from another feature's router.

### 3.3 Files Requiring Import Updates (Full List)

**Core consumers (app.config, app.database, app.security):**

- `app/main.py`
- `app/database.py` (during move: update self-import to app.core.config)
- `app/security.py` (during move: update self-import to app.core.config)
- `app/auth/router.py`, `app/auth/service.py`, `app/auth/dependencies.py`
- `app/tasks/router.py`, `app/tasks/repository.py`
- `app/insights/router.py`
- `app/chat/service.py`
- `app/telegram/router.py`, `app/telegram/adapter.py`, `app/telegram/scheduler.py`, `app/telegram/poller.py`

**Enums consumers (app.tasks.enums -> app.core.enums):**

- `app/tasks/models.py`, `app/tasks/schemas.py`, `app/tasks/repository.py`, `app/tasks/service.py`, `app/tasks/router.py`
- `app/insights/schemas.py`, `app/insights/service.py`
- `app/chat/service.py`

**Dependency getter consumers (router -> dependencies):**

- `app/insights/router.py`: `get_task_repository` from tasks.dependencies, `get_insights_service` from insights.dependencies
- `app/chat/router.py`: `get_task_repository` from tasks.dependencies
- `app/telegram/router.py`: all getters from telegram.dependencies, `get_task_repository` from tasks.dependencies
- `app/telegram/poller.py`: `get_telegram_service` from telegram.dependencies, `get_task_repository` from tasks.dependencies

**Test files:**

- `tests/conftest.py`: app.config, app.database, app.main, app.auth.router (change to app.auth.dependencies for get_auth_service), app.tasks.router (change to app.tasks.dependencies for get_task_repository)
- All test files that import from app

---

## 4. Step-by-Step Execution Sequence

### Phase 1: Core Infrastructure (Atomic)

| Step | Action | Verification |
|------|--------|---------------|
| 1.1 | Create `app/core/` directory | Directory exists |
| 1.2 | Create `app/core/__init__.py` (initially empty or with placeholder) | Package importable |
| 1.3 | Move `app/config.py` to `app/core/config.py` | File exists at new path |
| 1.4 | Update `app/core/config.py`: no internal app imports (already none) | — |
| 1.5 | Move `app/database.py` to `app/core/database.py` | File exists |
| 1.6 | Update `app/core/database.py`: `from app.config` -> `from app.core.config` | Linter passes |
| 1.7 | Move `app/security.py` to `app/core/security.py` | File exists |
| 1.8 | Update `app/core/security.py`: `from app.config` -> `from app.core.config` | Linter passes |
| 1.9 | Move `app/tasks/enums.py` to `app/core/enums.py` | File exists; delete `app/tasks/enums.py` |
| 1.10 | Update all imports: app.config -> app.core.config, app.database -> app.core.database, app.security -> app.core.security, app.tasks.enums -> app.core.enums | Run `pytest services/core-api/tests/` — all pass |
| 1.11 | Populate `app/core/__init__.py` with re-exports per section 2.3 | `from app.core import settings` works |

**Phase 1 Verification Step:** `cd services/core-api && python -m pytest tests/ -v --tb=short` — all tests pass.

---

### Phase 2: Feature Standardization — Dependencies Extraction

| Step | Action | Verification |
|------|--------|---------------|
| 2.1 | **Auth:** Remove `get_auth_service` from `app/auth/router.py`; ensure it exists only in `app/auth/dependencies.py`. Update router to import `get_auth_service` from dependencies | Auth tests pass |
| 2.2 | **Tasks:** Create `app/tasks/dependencies.py` with `get_task_repository`, `get_task_service` (moved from router). Update router to import from dependencies and remove function definitions | Tasks tests pass |
| 2.3 | **Insights:** Create `app/insights/dependencies.py` with `get_insights_service`. Create `app/insights/repository.py` (facade: optional, or minimal stub). Create `app/insights/models.py` (re-export Task from tasks.models or minimal). Update router to import from dependencies | Insights tests pass |
| 2.4 | **Chat:** Create `app/chat/dependencies.py` (minimal — chat uses get_task_repository from tasks). Create `app/chat/repository.py` (stub/facade). Create `app/chat/models.py` (minimal). Update router imports | Chat tests pass |
| 2.5 | **Telegram:** Create `app/telegram/dependencies.py` with `get_telegram_service`, `get_weekly_summary_service`, `_get_user_repo`, `_get_verification_repo`. Update router to import from dependencies and remove function definitions | Telegram tests pass |

**Cross-feature updates (during Phase 2):**

- `app/insights/router.py`: `from app.tasks.router import get_task_repository` -> `from app.tasks.dependencies import get_task_repository`; `from app.insights.dependencies import get_insights_service`
- `app/chat/router.py`: `from app.tasks.router import get_task_repository` -> `from app.tasks.dependencies import get_task_repository`
- `app/telegram/router.py`: All getters from `app.telegram.dependencies`; `get_task_repository` from `app.tasks.dependencies`
- `app/telegram/poller.py`: `from app.telegram.router import get_telegram_service` -> `from app.telegram.dependencies import get_telegram_service`; `from app.tasks.router import get_task_repository` -> `from app.tasks.dependencies import get_task_repository`

**Phase 2 Verification Step:** `cd services/core-api && python -m pytest tests/ -v` — all tests pass. Update `tests/conftest.py` overrides: `get_auth_service` and `get_task_repository` — ensure overrides target the new locations (`app.auth.dependencies`, `app.tasks.dependencies`).

---

### Phase 3: Telegram Workers and Main Wiring

| Step | Action | Verification |
|------|--------|---------------|
| 3.1 | Update `app/main.py`: `from app.telegram.scheduler` (unchanged); ensure scheduler uses `app.core.database` | Manual: `python -m uvicorn app.main:app --reload` starts |
| 3.2 | Update `app/telegram/scheduler.py`: `from app.config` -> `from app.core.config`; `from app.auth.repository` etc. (unchanged) | Linter passes |
| 3.3 | Update `app/telegram/poller.py`: imports from dependencies per Phase 2 | Poller tests pass if any |
| 3.4 | Update `app/auth/dependencies.py`: `get_database` from `app.core.database`; ensure no circular import with auth.router | Auth flow works |

**Phase 3 Verification Step:** Run full test suite; optionally run services via docker-compose and smoke-test health, auth, tasks, chat, insights, telegram endpoints.

---

### Phase 4: Test Suite and Conftest Alignment

| Step | Action | Verification |
|------|--------|---------------|
| 4.1 | Update `tests/conftest.py`: All `app.` imports to `app.core.` where applicable; `get_auth_service` override target `app.auth.dependencies`; `get_task_repository` override target `app.tasks.dependencies` | All tests pass |
| 4.2 | Update any test file that imports from moved modules | `pytest tests/` — 100% pass |
| 4.3 | Run linter (ruff/flake8) on entire app/ and tests/ | No new violations |

**Phase 4 Verification Step:** `cd services/core-api && python -m pytest tests/ -v --tb=short` — exit code 0.

---

## 5. Updated Final Tree Visualization

```
app/
├── __init__.py                    # Package marker (unchanged)
├── main.py                        # Entry point; imports from app.core, app.auth, app.tasks, etc.
│
├── core/                          # Foundation layer (NEW)
│   ├── __init__.py                # Re-exports: settings, get_database, database, validate_security_config, enums
│   ├── config.py                  # moved from app/
│   ├── database.py                # moved from app/
│   ├── security.py                # moved from app/
│   └── enums.py                   # moved from app/tasks/
│
├── auth/
│   ├── __init__.py                # auth_router, get_current_user
│   ├── router.py                  # Route handlers only; imports get_auth_service from dependencies
│   ├── service.py
│   ├── repository.py
│   ├── schemas.py
│   ├── models.py
│   └── dependencies.py            # get_auth_service, get_current_user, CurrentUser, bearer_scheme
│
├── tasks/
│   ├── __init__.py                # tasks_router
│   ├── router.py                  # Route handlers only; imports get_task_repository, get_task_service from dependencies
│   ├── service.py
│   ├── repository.py
│   ├── schemas.py
│   ├── models.py
│   └── dependencies.py            # get_task_repository, get_task_service (NEW)
│
├── insights/
│   ├── __init__.py                # insights_router
│   ├── router.py                  # Imports from tasks.dependencies, insights.dependencies
│   ├── service.py
│   ├── repository.py              # Minimal facade or stub (NEW)
│   ├── schemas.py
│   ├── models.py                  # Minimal or re-export (NEW)
│   └── dependencies.py            # get_insights_service (NEW)
│
├── chat/
│   ├── __init__.py                # chat_router
│   ├── router.py                  # Imports from tasks.dependencies
│   ├── service.py
│   ├── repository.py              # Minimal stub (NEW)
│   ├── schemas.py
│   ├── models.py                  # Minimal stub (NEW)
│   └── dependencies.py            # Minimal; may expose nothing or chat-specific helpers (NEW)
│
└── telegram/
    ├── __init__.py                # telegram_router
    ├── router.py                  # Route handlers only; all getters from dependencies
    ├── service.py
    ├── weekly_service.py
    ├── repository.py
    ├── weekly_repository.py
    ├── schemas.py
    ├── models.py
    ├── adapter.py
    ├── scheduler.py               # Background worker; imports from core, auth, tasks, insights, telegram
    ├── poller.py                  # Background worker; imports from core, telegram.dependencies, tasks.dependencies
    └── dependencies.py            # get_telegram_service, get_weekly_summary_service, _get_user_repo, _get_verification_repo (NEW)
```

**File count delta:** +1 (app/core/), +4 files moved to core, +5 new dependencies.py (tasks, insights, chat, telegram), +4 new files (insights/repository, insights/models, chat/repository, chat/models). Net new files: ~10.

---

## 6. Summary Checklist Before Migration

- [ ] Phase 1: Core exists; all app.config/database/security/enums imports updated
- [ ] Phase 2: All getters moved to dependencies; no router defines get_X
- [ ] Phase 3: main.py, scheduler, poller use app.core and new dependencies
- [ ] Phase 4: conftest and tests updated; full test suite passes
- [ ] Linter clean on app/ and tests/

**Awaiting command to start migration.**
