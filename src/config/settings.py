from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    APP_NAME: str = "Production-Ready FastAPI Service"
    ENVIRONMENT: str = "production"
    API_V1_STR: str = "/api/v1"

    # Example database configuration string
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/dbname"

    # Auto-load variable overrides from a local .env configuration file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = AppSettings()
