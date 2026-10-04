"""Pydantic models for profile-scoped workbook CRUD."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_thumbnail(value: str | None) -> str | None:
    if value in (None, ""):
        return value
    if len(value) > 1_400_100 or not value.startswith((
        "data:image/png;base64,",
        "data:image/jpeg;base64,",
        "data:image/webp;base64,",
    )):
        raise ValueError("Thumbnail must be a PNG, JPEG, or WebP image under 1 MB")
    return value


class WorkbookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=1000)
    thumbnail: str | None = Field(default=None, max_length=1_400_100)

    @field_validator("thumbnail")
    @classmethod
    def validate_thumbnail(cls, value: str | None) -> str | None:
        return _validate_thumbnail(value)


class WorkbookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    thumbnail: str | None = Field(default=None, max_length=1_400_100)

    @field_validator("thumbnail")
    @classmethod
    def validate_thumbnail(cls, value: str | None) -> str | None:
        return _validate_thumbnail(value)


class WorkbookRead(BaseModel):
    id: int
    title: str
    description: str
    thumbnail: str | None = None
    created_at: str
    updated_at: str
