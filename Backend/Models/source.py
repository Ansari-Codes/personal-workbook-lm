"""Request and response schemas for workbook sources."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceContentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    content: str = Field(max_length=5_000_000)
    folder: str = Field(default="", max_length=1024)


class SourceUrlCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    url: str = Field(min_length=1, max_length=2048)
    download: bool = True
    folder: str = Field(default="", max_length=1024)


class SourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    folder: str | None = Field(default=None, max_length=1024)


class SourceRead(BaseModel):
    id: int
    name: str
    description: str
    folder: str = ""
    kind: str
    source_url: str | None = None
    created_at: str
    updated_at: str


class SourceContentRead(BaseModel):
    id: int
    name: str
    content: str
    truncated: bool = False
