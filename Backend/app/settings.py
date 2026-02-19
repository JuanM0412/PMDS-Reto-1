from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "reto-multiagentes-backend"
    environment: str = "dev"
    cors_allow_origins: list[str] = ["http://localhost:5173"]

    database_url: str = "sqlite:///./app.db"

    # n8n
    n8n_webhook_url: AnyUrl | None = None
    n8n_api_key: str | None = None  # si protegen n8n con header

    request_timeout_seconds: float = 95.0
    step_wait_timeout_seconds: float = 90.0
    artifact_poll_interval_seconds: float = 1.0


settings = Settings()
