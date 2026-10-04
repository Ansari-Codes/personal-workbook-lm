"""Profile-scoped Caller CRUD operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from Pawm.Manage_Caller import Caller
from Pawm.Manage_Profile import Profile

from ..commons import STORAGE


def _profile(profile_id: int) -> Profile:
    return STORAGE.profiles.load(profile_id)


def _serialize_caller(caller: Caller) -> dict[str, Any]:
    data = caller.data
    content = Path(data["path"]).read_text(encoding="utf-8")
    return {
        "id": data["id"],
        "name": data["name"],
        "description": data.get("description", ""),
        "content": content,
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def list_callers(profile_id: int) -> list[dict[str, Any]]:
    return [_serialize_caller(item) for item in _profile(profile_id).callers.list()]


def create_caller(profile_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    caller = _profile(profile_id).callers.add(**fields)
    return _serialize_caller(caller)


def get_caller(profile_id: int, caller_id: int) -> dict[str, Any]:
    return _serialize_caller(_profile(profile_id).callers.load(caller_id))


def update_caller(
    profile_id: int, caller_id: int, updates: dict[str, Any]
) -> dict[str, Any]:
    callers = _profile(profile_id).callers
    content = updates.pop("content", None)
    caller = callers.update(caller_id, updates)
    if content is not None:
        caller = callers.update(caller_id, content=content)
    return _serialize_caller(caller)


def delete_caller(profile_id: int, caller_id: int) -> None:
    _profile(profile_id).callers.delete(caller_id)
