"""Request and response schemas for workbook outputs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OutputCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    content: str = Field(default="", max_length=5_000_000)
    folder: str = Field(default="", max_length=1024)


class OutputUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    content: str | None = Field(default=None, max_length=5_000_000)
    folder: str | None = Field(default=None, max_length=1024)


class OutputRead(BaseModel):
    id: int
    name: str
    description: str
    folder: str = ""
    size: int
    media_type: str
    created_at: str
    updated_at: str


class OutputContentRead(OutputRead):
    content: str | None = None
    content_base64: str | None = None
    encoding: str