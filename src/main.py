from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.routers import users

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """
    Handles startup resource allocation and cleanup during teardown.
    """
    print("[STARTUP] Initializing engine pools, loading cache stores...")
    yield
    print("[TEARDOWN] Safely flushing logs and terminating open database sockets...")

# Main Application Instance Setup
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=application_lifespan
)

# Standard Security Middleware Rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Configure domain specific restrictions in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL LEVEL DEFINITIONS (@app.get) ---
@app.get("/health", status_code=status.HTTP_200_OK, tags=["System Health"])
async def check_system_liveness():
    """
    Global diagnostic route. Handled directly by the application layer.
    Perfect for load balancers or orchestrators checking target availability.
    """
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

# --- SUB-ROUTER COMPOSITION AND INJECTION ---
# Mounts the localized endpoint routes with global structures
app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["User Management System"]
)


@asynccontextmanager
async def application_lifespan(app: FastAPI):
    from src.models.user_models import Base
    from src.config.database import async_engine

    print("[STARTUP] Provisioning physical schema models to active engine target...")
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    print("[TEARDOWN] Disposing active transaction engine thread pools cleanly...")
    await async_engine.dispose()
