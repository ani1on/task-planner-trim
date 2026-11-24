from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserUpdate(BaseModel):
    nick_name: str | None = Field(default=None, min_length=2, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserSettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: str


class UserSettingUpdate(BaseModel):
    theme: Literal["light", "dark"] | None = None
