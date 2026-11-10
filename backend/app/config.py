import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
APP_VERSION = '1.0.0'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str = Field(repr=False)
    web_port: int = 5173
    api_port: int = 8000
    cantina_data_dir: str | None = None

    @field_validator('database_url')
    @classmethod
    def mysql_only(cls, value: str) -> str:
        if not value.startswith('mysql+pymysql://'):
            raise ValueError('Use uma URL MySQL com o driver PyMySQL (mysql+pymysql://).')
        return value

    @property
    def backup_dir(self) -> Path:
        base = Path(self.cantina_data_dir or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CantinaEmDia')
        return base / 'backups'


settings = Settings()
