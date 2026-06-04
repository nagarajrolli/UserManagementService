from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    InactiveUserException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from src.models.user_models import UserModel
from src.repositories.user_repository import UserRepository
from src.schemas.user_schemas import (
    PaginatedResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

# Pre-computed bcrypt hash used when a login email is not found.
# Purpose: makes the "unknown email" code path take the same time as a real
# bcrypt verify, preventing timing-based email enumeration attacks.
# This hash was generated with bcrypt.hashpw(b"dummy-sentinel", bcrypt.gensalt(12))
_TIMING_DUMMY_HASH = "$2b$12$5ssysND0EFrqWU49lYiVNOipfS7UVVC.ZCXJvAGSncfzSORlee2oa"


class UserService:
    """
    Business Logic Layer — orchestrates use cases.
    Each public method = one use case.
    Raises domain exceptions (AppBaseException subclasses); never HTTPException.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(self, payload: UserCreate) -> UserModel:
        """
        Create a new user account.
        Raises UserAlreadyExistsException if the email is taken.
        """
        if await self._repo.get_by_email(payload.email):
            raise UserAlreadyExistsException(payload.email)

        return await self._repo.create(
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(self, email: str, password: str) -> TokenResponse:
        """
        Verify credentials and issue a JWT token pair.

        Timing-safe design:
          Always call verify_password regardless of whether the user exists.
          If the user is not found, verify against a pre-computed dummy hash.
          This ensures both code paths take ~the same time (bcrypt cost),
          preventing an attacker from detecting valid emails via response timing.
        """
        user = await self._repo.get_by_email(email)
        hash_to_check = user.hashed_password if user else _TIMING_DUMMY_HASH
        password_ok = verify_password(password, hash_to_check)

        if not user or not password_ok:
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InactiveUserException()

        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_by_id(self, user_id: int) -> UserModel:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id)
        return user

    async def get_all(self, page: int, page_size: int) -> PaginatedResponse[UserResponse]:
        """Return a paginated response with total count and page metadata."""
        skip = (page - 1) * page_size
        users, total = await self._repo.get_all(skip=skip, limit=page_size)
        pages = max(1, -(-total // page_size))  # ceiling division without math.ceil

        return PaginatedResponse[UserResponse](
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def update(self, user_id: int, payload: UserUpdate) -> UserModel:
        user = await self.get_by_id(user_id)
        # exclude_none=True: only apply fields the client actually sent
        changes = payload.model_dump(exclude_none=True)
        return await self._repo.update(user, **changes)

    async def delete(self, user_id: int) -> None:
        user = await self.get_by_id(user_id)
        await self._repo.delete(user)
