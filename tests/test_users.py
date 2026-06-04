"""
tests/test_users.py
--------------------
Integration tests for the User Management API.

Each test is fully isolated: a fresh DB schema is created and dropped
around every test function (see conftest.py manage_test_tables fixture).

Test naming convention: test_<endpoint>_<scenario>
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check_returns_200(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient, user_payload: dict):
    response = await async_client.post("/api/v1/users/", json=user_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_payload["email"]
    assert data["username"] == user_payload["username"]
    assert data["is_active"] is True
    assert data["role"] == "user"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    # Never leak the hashed password
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_user_duplicate_email_returns_409(
    async_client: AsyncClient, user_payload: dict
):
    await async_client.post("/api/v1/users/", json=user_payload)
    response = await async_client.post("/api/v1/users/", json=user_payload)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_user_invalid_email_returns_422(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/users/",
        json={"email": "not-an-email", "username": "user", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_user_short_password_returns_422(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/users/",
        json={"email": "valid@example.com", "username": "user", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_user_short_username_returns_422(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/users/",
        json={"email": "valid@example.com", "username": "ab", "password": "password123"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(
    async_client: AsyncClient, user_payload: dict, register_user: dict
):
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(
    async_client: AsyncClient, user_payload: dict, register_user: dict
):
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": "WrongPassword!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "AnyPassword1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(
    async_client: AsyncClient, user_payload: dict, register_user: dict
):
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401(
    async_client: AsyncClient, user_payload: dict, register_user: dict
):
    """Supplying an access token where a refresh token is expected must be rejected."""
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )
    access_token = login_response.json()["access_token"]

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},  # wrong token type
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_my_profile_authenticated(
    async_client: AsyncClient, user_payload: dict, auth_headers: dict
):
    response = await async_client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == user_payload["email"]


@pytest.mark.asyncio
async def test_get_my_profile_unauthenticated_returns_401(async_client: AsyncClient):
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_own_profile(
    async_client: AsyncClient, auth_headers: dict, register_user: dict
):
    user_id = register_user["id"]
    response = await async_client.patch(
        f"/api/v1/users/{user_id}",
        json={"username": "updated_username"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["username"] == "updated_username"


@pytest.mark.asyncio
async def test_list_users_requires_admin(
    async_client: AsyncClient, auth_headers: dict
):
    """Regular users cannot list all users."""
    response = await async_client.get("/api/v1/users/", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_requires_admin(
    async_client: AsyncClient, auth_headers: dict, register_user: dict
):
    """Regular users cannot delete accounts."""
    user_id = register_user["id"]
    response = await async_client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_id_requires_admin(
    async_client: AsyncClient, auth_headers: dict, register_user: dict
):
    user_id = register_user["id"]
    response = await async_client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 403
