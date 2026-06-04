from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import get_current_active_user, require_admin
from src.dependencies.database import get_async_db_session
from src.models.user_models import UserModel, UserRole
from src.schemas.user_schemas import (
    PaginatedResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from src.services.user_service import UserService

router = APIRouter()


# ---------------------------------------------------------------------------
# Registration (public — no auth required)
# ---------------------------------------------------------------------------

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a new user")
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_async_db_session),
) -> UserModel:
    # Open endpoint — no authentication required
    # Raises 409 if email already taken (UserAlreadyExistsException)
    return await UserService(db).register(payload)


# ---------------------------------------------------------------------------
# /me — must be declared BEFORE /{user_id} or FastAPI tries to cast "me" to int
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse, summary="Get your own profile")
async def get_my_profile(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    return current_user


# ---------------------------------------------------------------------------
# Admin: list all users (paginated)
# ---------------------------------------------------------------------------

@router.get("/", response_model=PaginatedResponse[UserResponse],
            summary="List all users (admin only)")
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    db: AsyncSession = Depends(get_async_db_session),
    _: UserModel = Depends(require_admin),  # _ = used only as auth guard
) -> PaginatedResponse[UserResponse]:
    return await UserService(db).get_all(page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Admin: get a single user by ID
# ---------------------------------------------------------------------------

@router.get("/{user_id}", response_model=UserResponse,
            summary="Get a user by ID (admin only)")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db_session),
    _: UserModel = Depends(require_admin),
) -> UserModel:
    return await UserService(db).get_by_id(user_id)


# ---------------------------------------------------------------------------
# Partial update — users can update themselves; admins can update anyone
# ---------------------------------------------------------------------------

@router.patch("/{user_id}", response_model=UserResponse,
              summary="Partially update a user")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    is_own_profile = current_user.id == user_id
    is_admin = current_user.role == UserRole.ADMIN

    if not is_own_profile and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own profile.",
        )
    return await UserService(db).update(user_id, payload)


# ---------------------------------------------------------------------------
# Admin: delete a user
# ---------------------------------------------------------------------------

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a user (admin only)")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db_session),
    _: UserModel = Depends(require_admin),
) -> None:
    await UserService(db).delete(user_id)
