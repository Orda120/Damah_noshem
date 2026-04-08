from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Damah_noshem API"
    app_env: str = "development"
    database_url: str = "sqlite:///./damah_noshem.db"
    jwt_secret: str = "change-me"
    access_policy_enabled: bool = False
    storage_mode: str = "filesystem"
    storage_base_path: Path = Path("./data/artifacts")
    archive_schema: str = "archive_catalog"
    session_cookie_name: str = "damah_session"
    session_max_age_seconds: int = 60 * 60 * 12
    cors_origins: list[str] = ["http://localhost:3000"]
    api_base_path: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
