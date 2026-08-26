"""Runtime configuration. Secrets come from the environment / `.env`, never code."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Only these three are expected for now (SPEC §3).
    database_url: str = "postgresql+psycopg://zaspro:zaspro@localhost:5432/zaspro"
    anthropic_api_key: str | None = None
    storage_root: Path = Path("./storage")


@lru_cache
def get_settings() -> Settings:
    return Settings()
