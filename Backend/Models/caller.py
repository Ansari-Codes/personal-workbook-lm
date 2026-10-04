"""Pydantic models for profile Caller CRUD."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CallerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    content: str = Field(min_length=1, max_length=200_000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_labels(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CallerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    content: str | None = Field(default=None, min_length=1, max_length=200_000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_labels(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CallerRead(BaseModel):
    id: int
    name: str
    description: str
    content: str
    created_at: str
    updated_at: str
