"""
src/routers/auth.py
--------------------
Authentication endpoints — login and token refresh.

Concepts covered:
- OAuth2PasswordRequestForm: standard OAuth2 form (username + password fields).
  The 'username' field carries the email here; this is the OAuth2 convention.
  The /docs "Authorize" dialog sends this form automatically.
- Token pair pattern:
    access_token  → sent with every API request (Authorization: Bearer <token>)
    refresh_token → stored securely by the client; used only to refresh.
  This limits the blast radius of a stolen access token to its short TTL.
- Stateless refresh: we trust the refresh token's signature. For higher security,
  store refresh tokens in a DB (token family rotation, revocation support).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, decode_token
from src.dependencies.database import get_async_db_session
from src.schemas.user_schemas import RefreshRequest, TokenResponse
from src.services.user_service import UserService

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login — receive access + refresh tokens",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db_session),
) -> TokenResponse:
    """
    Authenticate with email + password (form-encoded).

    OAuth2PasswordRequestForm uses **username** as the field name — send your
    email address there. The /docs Authorize dialog handles this automatically.

    Returns a short-lived access token and a long-lived refresh token.
    """
    service = UserService(db)
    return await service.authenticate(email=form_data.username, password=form_data.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new access token",
)
async def refresh_access_token(body: RefreshRequest) -> TokenResponse:
    """
    Provide a valid refresh token to receive a fresh access token.

    The refresh token is returned unchanged (stateless). For stricter security
    consider refresh token rotation: invalidate the old refresh token in the DB
    and issue a new one each time.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=body.refresh_token,
    )
