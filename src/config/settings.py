from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    APP_NAME: str = "User Management Service"
    ENVIRONMENT: str = "production"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str

    # Automatically loads configurations straight from your root .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = AppSettings()
