from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    business_name: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=120)
    manager_name: str = Field(default="", max_length=100)
    timezone: Literal["America/Sao_Paulo"] = "America/Sao_Paulo"


class SettingsRead(SettingsUpdate):
    model_config = ConfigDict(from_attributes=True)
    updated_at: datetime
