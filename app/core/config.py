from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_STORAGE_BUCKET: str = "imagens"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = "cafebugado/agendas_eventos"
    GITHUB_REPO_BACKEND: str = "cafebugado/backendEventos"

    # Observability
    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def _normaliza_log_level(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normaliza_environment(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    SENTRY_DSN: str = ""
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_EXPORTER_OTLP_HEADERS: str = ""
    SERVICE_NAME: str = "backend-eventos"
    ENVIRONMENT: Literal["development", "preview", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "VERCEL_ENV"),
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # OAuth
    OAUTH_REDIRECT_URL: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4200"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.SUPABASE_URL}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
