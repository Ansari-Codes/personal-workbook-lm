"""Profile CRUD operations backed by the shared storage instance."""

from __future__ import annotations

from typing import Any

from Pawm.Manage_Profile import Profile

from ..commons import STORAGE


def serialize_profile(profile: Profile) -> dict[str, Any]:
    data = profile.data
    return {
        "id": data["id"],
        "name": data["name"],
        "description": data.get("description", ""),
        "thumbnail": data.get("thumbnail"),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def list_profiles() -> list[dict[str, Any]]:
    return [serialize_profile(profile) for profile in STORAGE.profiles.list()]


def create_profile(
    name: str, description: str = "", thumbnail: str | None = None
) -> dict[str, Any]:
    return serialize_profile(STORAGE.profiles.create(
        name=name,
        description=description,
        thumbnail=thumbnail,
    ))


def get_profile(profile_id: int) -> dict[str, Any]:
    return serialize_profile(STORAGE.profiles.load(profile_id))


def update_profile(profile_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    profile = STORAGE.profiles.load(profile_id)
    profile.update(**updates)
    return serialize_profile(profile)


def delete_profile(profile_id: int) -> None:
    STORAGE.profiles.delete(profile_id)
