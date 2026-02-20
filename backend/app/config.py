from __future__ import annotations

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General
    app_name: str = "agents-backend"
    environment: str = "development"
    debug: bool = False

    # CORS
    cors_allow_origins: list[str] = ["http://localhost:5173"]

    # PostgreSQL
    database_url: str = "postgresql://postgres:postgres@localhost:5432/agents_db"

    # N8N
    n8n_base_url: str = "http://localhost:5678"
    n8n_api_key: str | None = None
    n8n_request_timeout: float = 90.0

    # Public URL of this backend (used to build callback URLs sent to n8n)
    public_base_url: str = "http://localhost:8000"


settings = Settings()
