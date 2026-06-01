# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from src.config.settings import settings
from src.routers import users

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    # Optional fallback: creates tables on startup if Alembic migrations aren't executed manually
    from src.models.user_models import Base
    from src.config.database import async_engine
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()

app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=application_lifespan)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["System Health"])
async def check_system_liveness():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["User Management System"])
