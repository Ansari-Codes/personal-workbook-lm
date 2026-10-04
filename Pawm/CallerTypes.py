"""Unified input/output contracts for pluggable model callers."""

from __future__ import annotations

from typing import Any, TypedDict
from typing_extensions import NotRequired


class MODEL_ITEM(TypedDict):
    id: str
    name: str
    owned_by: NotRequired[str]
    created: NotRequired[int]
    context_window: NotRequired[int]
    capabilities: NotRequired[list[str]]


class MODEL_OUTPUT(TypedDict):
    success: bool
    models: list[MODEL_ITEM]
    error: NotRequired[str]
    raw: NotRequired[dict[str, Any]]


class CALLER_MESSAGE(TypedDict):
    role: str
    content: str
    tool_calls: NotRequired[list[dict[str, Any]]]


class CALLER_MEDIA_OUTPUT(TypedDict):
    name: str
    media_type: str
    content: bytes
    folder: NotRequired[str]


class INVOKE_OUTPUT(TypedDict):
    success: bool
    model: NotRequired[str]
    text: NotRequired[str]
    choices: NotRequired[list[dict[str, Any]]]
    tool_calls: NotRequired[list[dict[str, Any]]]
    message: NotRequired[CALLER_MESSAGE]
    usage: NotRequired[dict[str, Any]]
    finish_reason: NotRequired[str | None]
    media: NotRequired[list[CALLER_MEDIA_OUTPUT]]
    reasoning: NotRequired[str]
    raw: NotRequired[dict[str, Any]]
    error: NotRequired[str]
