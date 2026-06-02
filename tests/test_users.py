import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_check_system_liveness(async_client: AsyncClient):
    """Verifies that the core global health check endpoint returns 200 OK."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "environment": "production"}


@pytest.mark.asyncio
async def test_register_user_successfully(async_client: AsyncClient):
    """Verifies that a valid payload registers a new user in the database."""
    payload = {
        "email": "qa_engineer@domain.com",
        "username": "qa_tester",
        "password": "superSecurePassword99"
    }
    response = await async_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "qa_engineer@domain.com"
    assert data["username"] == "qa_tester"
    assert "id" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_registration_fails_on_duplicate_email(async_client: AsyncClient):
    """Verifies that registering a duplicate email triggers a 400 error."""
    payload = {
        "email": "duplicate@domain.com",
        "username": "user_one",
        "password": "securePassword1"
    }

    # First registration should pass smoothly
    res1 = await async_client.post("/api/v1/users/", json=payload)
    assert res1.status_code == 201

    # Second registration with the exact same email must fail
    payload["username"] = "user_two"
    res2 = await async_client.post("/api/v1/users/", json=payload)
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Email already registered."
