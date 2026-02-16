"""Application configuration management."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    # Application
    app_name: str = "Seal-Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Paths
    soul_dir: Path = Path("soul")

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Database
    database_url: str = "postgresql+asyncpg://seal:seal@localhost:5432/seal_agent"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me-in-production"

    # Heartbeat
    heartbeat_enabled: bool = True

    model_config = {"env_prefix": "SEAL_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
