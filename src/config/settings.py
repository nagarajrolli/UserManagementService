import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# ENV_FILE env var lets you swap configs: ENV_FILE=.env.local pytest
env_file_target = os.getenv("ENV_FILE", ".env")


class AppSettings(BaseSettings):
    # Application
    APP_NAME: str = "User Management Engine"
    ENVIRONMENT: str = "production"
    API_V1_STR: str = "/api/v1"

    # Database — required, no default; will raise on startup if missing
    DATABASE_URL: str

    # JWT Security — required, no default
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS origins (JSON array in env var)
    # e.g. CORS_ORIGINS='["https://myapp.com"]'
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    model_config = SettingsConfigDict(
        env_file=env_file_target,
        extra="ignore",
    )


settings = AppSettings()
