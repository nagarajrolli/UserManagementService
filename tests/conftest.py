# tests/conftest.py
import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.main import app
from src.models.user_models import Base
from src.dependencies.database import get_async_db_session

# Connection string pointing to your live Docker container running on localhost
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:admin@127.0.0.1:5432/userManagementServiceTestDB"

# NullPool forces the driver to open/close connection sockets instantly,
# preventing cross-test task overlaps and the "another operation in progress" error.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="function", autouse=True)
async def manage_test_tables():
    """
    Safely sets up database tables before each test execution
    and drops them immediately afterward to maintain clean data state.
    """
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a fresh database transaction context manager per test function."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an asynchronous client wrapper for calling your FastAPI endpoints.
    Fixes the 'NoneType send' crash by mirroring the original AsyncGenerator signature.
    """

    # CRITICAL: This must match the exact signature (AsyncGenerator) of your real dependency
    async def _mock_get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Safely swap your real database router hook with our mocked session data
    app.dependency_overrides[get_async_db_session] = _mock_get_async_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    # Clear the overrides immediately after the test runs to prevent state contamination
    app.dependency_overrides.clear()
