from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field

from src.models.user_models import UserRole


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    # Payload for POST /users/ — open registration
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    # All fields Optional — PATCH sends only what changed
    # model_dump(exclude_none=True) in the service strips the rest
    username: str | None = Field(None, min_length=3, max_length=50)
    is_active: bool | None = None


class UserResponse(UserBase):
    # What the API returns — never includes hashed_password
    id: int
    is_active: bool
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    # Returned by POST /auth/login and POST /auth/refresh
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # Body for POST /auth/refresh
    refresh_token: str


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    # Generic paginated wrapper — reuse for any list endpoint
    # Usage: PaginatedResponse[UserResponse]
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
