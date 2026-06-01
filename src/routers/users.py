# src/routers/users.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.schemas.user_schemas import UserCreate, UserResponse
from src.models.user_models import UserModel
from src.dependencies.database import get_async_db_session

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_database_user(payload: UserCreate, db: AsyncSession = Depends(get_async_db_session)):
    query = select(UserModel).where(UserModel.email == payload.email)
    query_execution = await db.execute(query)
    if query_execution.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    db_user = UserModel(
        email=payload.email,
        username=payload.username,
        hashed_password=f"hashed_{payload.password}"  # In production, use bcrypt/argon2 to hash passwords!
    )
    db.add(db_user)
    await db.flush()
    return db_user
