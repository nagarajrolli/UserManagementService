"""
tests/conftest.py
------------------
Shared pytest fixtures for all tests.

Concepts covered:
- Test isolation: each test gets a fresh schema (create_all / drop_all) so tests
  can't interfere with each other through leftover data.
- Dependency override: app.dependency_overrides swaps get_async_db_session with a
  fixture-supplied session. This is the FastAPI-idiomatic way to inject a test DB
  without monkey-patching.
- NullPool: disables connection pooling in tests. Each test gets a brand-new
  connection, which avoids shared state between async test runs.
- Scope strategy:
    manage_test_tables → function scope: fresh schema per test (safest).
    db_session         → function scope: separate transaction per test.
    async_client       → function scope: fresh HTTP client per test.
- Helper fixtures (register_user, login_user, auth_headers): DRY — every test
  that needs an authenticated user calls auth_headers instead of repeating
  the registration + login flow.
"""

from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import settings
from src.dependencies.database import get_async_db_session
from src.main import app
from src.models.user_models import Base

# ---------------------------------------------------------------------------
# Test database URL — same host config, different database name
# ---------------------------------------------------------------------------
_parsed = make_url(settings.DATABASE_URL)
_test_url = _parsed._replace(host="127.0.0.1", database="userManagementServiceTestDB")
TEST_DATABASE_URL: str = _test_url.render_as_string(hide_password=False)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Schema lifecycle — runs around every test function
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function", autouse=True)
async def manage_test_tables():
    """Drop and recreate all tables before each test for full isolation."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Database session fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession scoped to the test.
    Rolls back after each test so uncommitted data doesn't leak.
    """
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# HTTP client fixture — wires the test DB into the app
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Return an HTTPX AsyncClient pointed at the test app, with the test DB injected.
    dependency_overrides replaces get_async_db_session for the duration of the test.
    """

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_db_session] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper fixtures — reduce boilerplate in tests
# ---------------------------------------------------------------------------

@pytest.fixture
def user_payload() -> dict:
    """A valid user registration payload."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePass99!",
    }


@pytest.fixture
async def register_user(async_client: AsyncClient, user_payload: dict) -> dict:
    """Register a user and return the response JSON."""
    response = await async_client.post("/api/v1/users/", json=user_payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def auth_headers(async_client: AsyncClient, user_payload: dict, register_user: dict) -> dict:
    """
    Register + login a user and return Authorization headers.
    Usage: response = await async_client.get("/api/v1/users/me", headers=auth_headers)
    """
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
