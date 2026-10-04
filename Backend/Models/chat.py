"""Request and response schemas for workbook chat completions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)

class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=100_000)
    model: str = Field(min_length=1, max_length=256)
    caller_id: int = Field(gt=0)
    api_key_id: int = Field(gt=0)
    endpoint_name: str = Field(default="chat", min_length=1, max_length=120)
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)
    context_length: int = Field(ge=0, le=100)
    max_tool_calls: int | None = Field(default=4, gt=0)
    stream: bool = False
    history: list[ChatTurn] = Field(default_factory=list, max_length=100)
    additional_parameters: dict[str, Any] = Field(default_factory=dict)


class ChatEvent(BaseModel):
    role: Literal["tool_call", "tool_output", "thinking", "reasoning"]
    content: str
    name: str


class ChatResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    model: str
    usage: dict[str, Any] = Field(default_factory=dict)
    events: list[ChatEvent] = Field(default_factory=list)
