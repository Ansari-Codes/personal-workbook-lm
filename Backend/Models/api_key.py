"""Pydantic models for profile API-key CRUD."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    secret: str = Field(min_length=1, max_length=4096)
    base_url: str = Field(min_length=1, max_length=2048)
    endpoints: dict[str, str] = Field(min_length=1)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("endpoints")
    @classmethod
    def validate_endpoints(cls, endpoints: dict[str, str]) -> dict[str, str]:
        normalized = {name.strip(): path.strip() for name, path in endpoints.items()}
        if not normalized or any(not name or not path for name, path in normalized.items()):
            raise ValueError("Endpoint names and paths must not be empty")
        return normalized


class APIKeyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    secret: str | None = Field(default=None, min_length=1, max_length=4096)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    endpoints: dict[str, str] | None = None
    meta: dict[str, Any] | None = None

    @field_validator("endpoints")
    @classmethod
    def validate_endpoints(cls, endpoints: dict[str, str] | None) -> dict[str, str] | None:
        if endpoints is None:
            return None
        normalized = {name.strip(): path.strip() for name, path in endpoints.items()}
        if not normalized or any(not name or not path for name, path in normalized.items()):
            raise ValueError("Endpoint names and paths must not be empty")
        return normalized


class APIKeyRead(BaseModel):
    id: int
    name: str
    description: str
    base_url: str
    endpoints: dict[str, str]
    key_preview: str
    meta: dict[str, Any]
    created_at: str
    updated_at: str


class APIModelOption(BaseModel):
    id: str
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
