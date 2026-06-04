"""
src/repositories/user_repository.py
-------------------------------------
Data Access Layer (DAL) — the Repository Pattern.

Concepts covered:
- Repository Pattern: all raw SQL/ORM operations live here. Routers and services
  never import `select`, `func`, or any SQLAlchemy construct directly.
  Benefits: swap the DB engine in one place; mock at test time by swapping the
  repository, not the entire database stack.
- flush() vs commit():
    flush()  → sends SQL to the DB within the current transaction; row is visible
               within the same session but NOT committed. The session dependency
               in dependencies/database.py owns the commit/rollback lifecycle.
    commit() → finalises the transaction. Do NOT call this here — the dependency
               layer controls the transaction boundary.
- refresh(): re-reads the row from the DB after flush so server-computed fields
  (id, created_at, updated_at) are populated on the returned object.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_models import UserModel, UserRole


class UserRepository:
    """
    Encapsulates all database operations for UserModel.
    Instantiated per-request inside the service layer.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_id(self, user_id: int) -> UserModel | None:
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalars().first()

    async def get_by_email(self, email: str) -> UserModel | None:
        result = await self.db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalars().first()

    async def get_all(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[UserModel], int]:
        """Return a page of users and the total count in a single round-trip pair."""
        total_result = await self.db.execute(select(func.count(UserModel.id)))
        total: int = total_result.scalar_one()

        users_result = await self.db.execute(
            select(UserModel).offset(skip).limit(limit).order_by(UserModel.id)
        )
        users = list(users_result.scalars().all())
        return users, total

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        email: str,
        username: str,
        hashed_password: str,
        role: UserRole = UserRole.USER,
    ) -> UserModel:
        """
        Insert a new user row and return the fully-populated ORM object.
        Uses keyword-only args (*) to prevent positional mix-ups.
        """
        user = UserModel(
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()        # send INSERT, get auto-generated id
        await self.db.refresh(user)  # load server_default timestamps
        return user

    async def update(self, user: UserModel, **fields) -> UserModel:
        """
        Apply *fields* to *user* and flush.
        The caller passes only the fields to change (already filtered with
        model_dump(exclude_none=True) in the service layer).
        """
        for key, value in fields.items():
            setattr(user, key, value)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: UserModel) -> None:
        await self.db.delete(user)
        await self.db.flush()
