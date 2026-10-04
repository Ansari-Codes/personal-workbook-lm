"""Pydantic metadata models for profile tool packages."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ToolUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)


class ToolRead(BaseModel):
    id: int
    title: str
    description: str
    created_at: str
    updated_at: str
