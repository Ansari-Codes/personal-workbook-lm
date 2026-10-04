"""Profile-scoped workbook CRUD operations."""

from __future__ import annotations

from typing import Any

from Pawm.Manage_Profile import Profile
from Pawm.Manage_Workbook import Workbook

from .builtins import ensure_profile_builtins
from ..commons import STORAGE


def _profile(profile_id: int) -> Profile:
    return STORAGE.profiles.load(profile_id)


def _serialize_workbook(workbook: Workbook) -> dict[str, Any]:
    data = workbook.data
    return {
        "id": data["id"],
        "title": data["title"],
        "description": data.get("description", ""),
        "thumbnail": data.get("thumbnail"),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def list_workbooks(profile_id: int) -> list[dict[str, Any]]:
    profile = _profile(profile_id)
    return [_serialize_workbook(workbook) for workbook in profile.workbooks.list()]


def create_workbook(
    profile_id: int, title: str, description: str = "", thumbnail: str | None = None
) -> dict[str, Any]:
    profile = _profile(profile_id)
    default_caller_id, default_tool_ids = ensure_profile_builtins(profile)
    workbook = profile.workbooks.create(title=title, description=description, thumbnail=thumbnail)
    workbook.config.set("selected_caller_id", default_caller_id)
    workbook.config.set("selected_tool_ids", default_tool_ids)
    workbook.config.set("use_tools", bool(default_tool_ids))
    return _serialize_workbook(workbook)


def get_workbook(profile_id: int, workbook_id: int) -> dict[str, Any]:
    profile = _profile(profile_id)
    return _serialize_workbook(profile.workbooks.load(workbook_id))


def update_workbook(
    profile_id: int, workbook_id: int, updates: dict[str, Any]
) -> dict[str, Any]:
    profile = _profile(profile_id)
    workbook = profile.workbooks.load(workbook_id)
    workbook.update(**updates)
    return _serialize_workbook(workbook)


def delete_workbook(profile_id: int, workbook_id: int) -> None:
    profile = _profile(profile_id)
    profile.workbooks.delete(workbook_id)


def get_workbook_config(profile_id: int, workbook_id: int) -> dict[str, Any]:
    profile = _profile(profile_id)
    return profile.workbooks.load(workbook_id).config.all()


def update_workbook_config(
    profile_id: int, workbook_id: int, updates: dict[str, Any]
) -> dict[str, Any]:
    profile = _profile(profile_id)
    config = profile.workbooks.load(workbook_id).config
    for key, value in updates.items():
        config.set(key, value)
    return config.all()
