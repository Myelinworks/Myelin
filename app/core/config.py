from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Myelin Backend"
    environment: str = "development"

    database_url: str
    redis_url: str

    cors_origins: list[str] = ["http://localhost:3000"]

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwks_url: str = ""

    # The valid-role universe, kept in config so a new role is an env change, not a code
    # change. Which of these roles get cross-ownership read access is a business rule, not
    # a config knob -- see authorization_service.INSTRUCTOR_ROLES.
    app_roles: list[str] = ["student", "instructor", "admin"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
