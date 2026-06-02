# src/config/settings.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically pick up '.env.local' if passed, otherwise fall back to default '.env'
env_file_target = os.getenv("ENV_FILE", ".env")
print(f"[BOOT] Initializing system using configuration mask: {env_file_target}")

class AppSettings(BaseSettings):
    APP_NAME: str = "User Management Engine"
    ENVIRONMENT: str = "production"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=env_file_target, extra="ignore")

settings = AppSettings()
