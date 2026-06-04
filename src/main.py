import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.core.exceptions import register_exception_handlers
from src.middleware.logging import RequestLoggingMiddleware
from src.routers import auth, users

# ---------------------------------------------------------------------------
# Logging — basicConfig configures the root logger.
# In production swap this for structlog or a JSON formatter so log aggregators
# (Datadog, CloudWatch, ELK) can parse fields automatically.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — replaces deprecated on_event("startup" / "shutdown")
# Code before yield = startup; code after yield = shutdown.
# FastAPI guarantees the shutdown block runs even if the app crashes.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.config.database import async_engine
    from src.models.user_models import Base

    logger.info("Starting up | environment=%s", settings.ENVIRONMENT)
    # create_all is a safety net — run `alembic upgrade head` in CI/CD instead
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Shutting down | disposing DB connection pool")
    await async_engine.dispose()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Production-grade User Management Service — FastAPI + PostgreSQL.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware (declared first = outermost wrapper)
# CORS must be outermost so pre-flight OPTIONS requests bypass auth/logging.
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"],
         summary="Liveness probe")
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


app.include_router(auth.router,  prefix=f"{settings.API_V1_STR}/auth",  tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
