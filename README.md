# User Management Service

A production-grade REST API for user management built with **FastAPI** and **PostgreSQL**. Demonstrates core FastAPI patterns and a clean layered architecture suitable for real-world projects.

## Features

- User registration, login, and profile management
- JWT authentication with access + refresh token pair
- Role-based access control (USER / ADMIN)
- Async database access via SQLAlchemy 2.0 + asyncpg
- Database migrations with Alembic
- Request logging with correlation IDs
- Pydantic v2 request validation and response serialization

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.136 |
| Server | Uvicorn |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Driver | asyncpg |
| Migrations | Alembic |
| Auth | python-jose (JWT) + bcrypt |
| Validation | Pydantic v2 |

## Project Structure

```
src/
├── main.py                  # App factory, middleware, exception handlers
├── config/
│   ├── settings.py          # Pydantic-based config (reads from .env)
│   └── database.py          # Async SQLAlchemy engine and session factory
├── routers/                 # HTTP endpoints (auth, users)
├── services/                # Business logic layer
├── repositories/            # Data access layer (all SQL lives here)
├── models/                  # SQLAlchemy ORM models
├── schemas/                 # Pydantic request/response models
├── dependencies/            # FastAPI Depends() providers (auth, DB session)
├── core/                    # Security (JWT, bcrypt), exception hierarchy
└── middleware/              # Request logging
tests/
alembic/                     # Migration scripts
```

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL running locally (or use Docker Compose)

### Option A — Local Setup

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env.local
# Edit .env.local — set DATABASE_URL and SECRET_KEY

# Run migrations
$env:ENV_FILE=".env.local"; alembic upgrade head

# Start the server
$env:ENV_FILE=".env.local"; uvicorn src.main:app --reload
```

### Option B — Docker Compose

```bash
docker-compose up --build
```

This starts PostgreSQL and the API together. No manual configuration needed.

## API

Once running, interactive docs are available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | — | Liveness probe |
| POST | `/api/v1/auth/login` | — | Login, receive JWT tokens |
| POST | `/api/v1/auth/refresh` | — | Exchange refresh token for new access token |
| POST | `/api/v1/users/` | — | Register a new user |
| GET | `/api/v1/users/me` | user | Get your own profile |
| PATCH | `/api/v1/users/{id}` | user / admin | Update profile |
| GET | `/api/v1/users/` | admin | List all users (paginated) |
| GET | `/api/v1/users/{id}` | admin | Get user by ID |
| DELETE | `/api/v1/users/{id}` | admin | Delete a user |

## Running Tests

```bash
# All tests (no external DB needed — uses in-memory test DB)
pytest

# Single test
pytest tests/test_users.py::test_register_user_success -v
```

## Key FastAPI Concepts Demonstrated

1. **Dependency Injection** — `Depends()` wires DB sessions and auth guards through the call chain
2. **Layered architecture** — Router → Service → Repository separation of concerns
3. **Async database** — Full async stack with SQLAlchemy 2.0 + asyncpg
4. **Alembic migrations** — Version-controlled schema changes
5. **Pydantic v2 schemas** — Separate request/response models; passwords never leak in responses
6. **Custom exception hierarchy** — Domain exceptions translate to HTTP responses via global handlers
7. **JWT auth** — Access + refresh token pattern with token-type guards
8. **Router organization** — Prefix-based grouping, route ordering (e.g. `/me` before `/{id}`)