# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python FastAPI user management service demonstrating production-grade patterns: async PostgreSQL (asyncpg), JWT auth, role-based access control, Alembic migrations, and layered architecture.

## Commands

### Run the Application

**Local (requires PostgreSQL running on localhost):**
```powershell
$env:ENV_FILE=".env.local"; uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Docker Compose (includes PostgreSQL):**
```powershell
docker-compose up --build
```
API: http://localhost:8000 | Docs: http://localhost:8000/docs

### Database Migrations

```powershell
# Apply migrations
$env:ENV_FILE=".env.local"; alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "description"

# Rollback one migration
$env:ENV_FILE=".env.local"; alembic downgrade -1
```

### Tests

```powershell
# All tests
pytest

# Single test file
pytest tests/test_users.py

# Single test by name
pytest tests/test_users.py::test_register_user_success -v

# Filter by keyword
pytest -k "test_login" -v
```

Tests use `pytest-asyncio` with `asyncio_mode = auto` (set in `pytest.ini`). The `conftest.py` creates an isolated test database and overrides the app's DB dependency — no external DB required for tests.

## Architecture

### Layered Structure

```
Router → Service → Repository → SQLAlchemy ORM → PostgreSQL
```

- **`src/routers/`** — HTTP endpoints, status codes, request/response mapping
- **`src/services/`** — Business logic, domain rules, raises domain exceptions
- **`src/repositories/`** — All ORM queries; no business logic here
- **`src/schemas/`** — Pydantic models for request validation and response serialization
- **`src/models/`** — SQLAlchemy ORM models (`UserModel`, `UserRole` enum)
- **`src/core/`** — Cross-cutting concerns: JWT/password security, exception hierarchy
- **`src/dependencies/`** — FastAPI `Depends()` providers: DB session, current user, admin guard
- **`src/middleware/`** — Request logging with correlation IDs

### Dependency Injection Flow

FastAPI's `Depends()` wires the full stack:
- `get_async_db_session` (`dependencies/database.py`) — per-request `AsyncSession`, auto-commits or rolls back
- `get_current_user` (`dependencies/auth.py`) — validates JWT, loads user from DB
- `require_admin` — wraps `get_current_user` and enforces `UserRole.ADMIN`

### Configuration

`src/config/settings.py` uses `pydantic-settings` to load from `.env` files. The active env file is controlled by the `ENV_FILE` environment variable:
- `.env.local` — local dev (DB host: `localhost`)
- `.env` — Docker Compose (DB host: `postgres` service name)

### Authentication

- Passwords: bcrypt (direct, not via passlib — passlib had compatibility issues)
- JWT: access tokens (30 min) + refresh tokens (7 days), both carry a `type` claim to prevent token substitution
- Login uses a dummy hash check when user not found to prevent email enumeration timing attacks

### Exception Handling

`src/core/exceptions.py` defines a domain exception hierarchy. Global handlers in `src/main.py` map these to HTTP responses (e.g., `UserAlreadyExistsError` → 409, `AuthenticationError` → 401). Routers and services raise domain exceptions — never raw `HTTPException`.

### API Routes

All user/auth routes are under `/api/v1/`:

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/auth/login` | — |
| POST | `/api/v1/auth/refresh` | — |
| POST | `/api/v1/users/` | — |
| GET | `/api/v1/users/me` | user |
| PATCH | `/api/v1/users/{id}` | user (own) or admin |
| GET | `/api/v1/users/` | admin |
| GET | `/api/v1/users/{id}` | admin |
| DELETE | `/api/v1/users/{id}` | admin |
| GET | `/health` | — |

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | App factory, lifespan, middleware, global exception handlers, route registration |
| `src/config/settings.py` | All environment-driven config (DB URL, JWT secret, CORS origins) |
| `src/config/database.py` | Async SQLAlchemy engine and `AsyncSession` factory |
| `alembic/env.py` | Async-compatible Alembic runner |
| `tests/conftest.py` | Test DB setup, `async_client` fixture, auth helper fixtures |
| `.env.example` | Template listing all required environment variables |