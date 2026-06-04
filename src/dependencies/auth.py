from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.core.security import decode_token
from src.dependencies.database import get_async_db_session
from src.models.user_models import UserModel, UserRole
from src.repositories.user_repository import UserRepository

# tokenUrl tells OpenAPI (/docs Authorize dialog) where to POST credentials
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db_session),
) -> UserModel:
    """
    Decode the JWT, check the 'type' claim, and load the user from the DB.
    Raises 401 for any token problem: expired, tampered, wrong type, user gone.

    Dependency chain:
        get_current_user
        └── oauth2_scheme  (extracts Bearer token from Authorization header)
        └── get_async_db_session  (provides DB session)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_id(int(user_id_str))
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Extends get_current_user: additionally rejects deactivated accounts.
    Use on any endpoint a normal authenticated user can access.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )
    return current_user


async def require_admin(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    """
    Role guard: only ADMIN users may proceed.
    Depends on get_current_active_user, so it also enforces authentication
    and active status automatically.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges are required.",
        )
    return current_user
