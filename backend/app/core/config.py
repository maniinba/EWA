"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object.

    Values are read from environment variables (or a local ``.env`` file).
    Defaults are chosen so the app runs out-of-the-box against SQLite with no
    external services, while still supporting a production PostgreSQL setup.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General ---
    app_name: str = "EWA Dashboard"
    environment: str = "development"
    api_prefix: str = "/api"

    # --- Database ---
    # Defaults to a local SQLite file so the app runs without a DB server.
    # In production set e.g.:
    #   postgresql+psycopg2://ewa:ewa@postgres:5432/ewa
    database_url: str = "sqlite:///./ewa.db"

    # --- Security ---
    # CHANGE THIS in production. Used to sign JWTs and encrypt stored secrets.
    secret_key: str = "dev-secret-change-me-in-production-please-32chars"
    access_token_expire_minutes: int = 60 * 24
    algorithm: str = "HS256"

    # Seed admin created on first startup (dev convenience).
    first_admin_email: str = "admin@example.com"
    first_admin_password: str = "admin"

    # --- File storage ---
    upload_dir: str = "./uploads"
    max_upload_mb: int = 50

    # --- SAP for Me connector ---
    sapforme_base_url: str = "https://api.support.sap.com"
    sapforme_token_url: str = "https://accounts.sap.com/oauth2/token"

    # --- Celery / Redis (optional) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
