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

    # Voyage embeddings (uses Anthropic/Voyage API)
    voyage_api_key: str = ""  # Falls back to anthropic_api_key if empty
    voyage_model: str = "voyage-3"
    voyage_dimensions: int = 1024

    # Database
    database_url: str = "postgresql+asyncpg://seal:seal@localhost:5432/seal_agent"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me-in-production"
    api_cors_origins: str = "http://localhost:3000"

    # Heartbeat
    heartbeat_enabled: bool = True

    # Email integration
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Seal-Agent"
    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""

    # HubSpot integration
    hubspot_api_key: str = ""
    hubspot_base_url: str = "https://api.hubapi.com"

    # Slack integration
    slack_bot_token: str = ""
    slack_signing_secret: str = ""

    model_config = {"env_prefix": "SEAL_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
