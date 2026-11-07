from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
APP_VERSION = '0.3.0'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = Field(repr=False)
    api_port: int = 8000
    web_port: int = 5173
    cantina_data_dir: str | None = None
    cantina_auto_backup: bool = True

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("Use uma URL PostgreSQL com o driver psycopg.")
        return value


settings = Settings()
