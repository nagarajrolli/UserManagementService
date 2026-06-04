"""
alembic/env.py
---------------
Alembic migration environment — configured for async SQLAlchemy.

Concepts covered:
- Async Alembic: standard Alembic uses synchronous connections. We use
  run_async_migrations() with AsyncEngine.connect() to stay fully async.
- target_metadata: points Alembic at our ORM's Base.metadata so it can
  auto-detect model changes and generate migrations automatically.
- DATABASE_URL from settings: Alembic reads the URL at runtime from the same
  source as the app — no duplication, no drift between migrations and the app.
- render_as_batch=True: needed for SQLite (ALTER TABLE workaround), harmless
  on PostgreSQL. Keep it for portability.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import your model metadata
# ---------------------------------------------------------------------------
# Add every model module that Alembic needs to see for autogenerate.
# As you add new models, import their Base or the models themselves here.
from src.models.user_models import Base  # noqa: E402

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Database URL — read from app settings so it always stays in sync
# ---------------------------------------------------------------------------
# We import settings here so Alembic uses the same .env loading logic as the app.
# This means running `ENV_FILE=.env.local alembic upgrade head` works correctly.
from src.config.settings import settings  # noqa: E402

DATABASE_URL = settings.DATABASE_URL


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL scripts without a live DB connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Useful for generating SQL scripts to review before applying.
    Usage: alembic upgrade head --sql > migration.sql
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (connect to DB and apply changes directly)
# ---------------------------------------------------------------------------
def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside a sync wrapper."""
    engine = create_async_engine(DATABASE_URL)

    # run_sync() lets us use the synchronous Alembic API on an async connection.
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
