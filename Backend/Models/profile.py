"""Pydantic models for profile CRUD endpoints."""

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


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    thumbnail: str | None = Field(default=None, max_length=1_400_100)

    @field_validator("thumbnail")
    @classmethod
    def validate_thumbnail(cls, value: str | None) -> str | None:
        return _validate_thumbnail(value)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    thumbnail: str | None = Field(default=None, max_length=1_400_100)

    @field_validator("thumbnail")
    @classmethod
    def validate_thumbnail(cls, value: str | None) -> str | None:
        return _validate_thumbnail(value)


class ProfileRead(BaseModel):
    id: int
    name: str
    description: str
    thumbnail: str | None = None
    created_at: str
    updated_at: str
