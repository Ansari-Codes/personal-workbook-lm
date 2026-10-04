"""Workbook-scoped source CRUD and content operations."""

from __future__ import annotations

from typing import Any
from urllib.request import urlopen

from Pawm.Manage_Profile import Profile
from Pawm.Manage_Source import Source

from ..commons import STORAGE, normalize_folder

MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_PREVIEW_BYTES = 1024 * 1024


def _sources(profile_id: int, workbook_id: int):
    profile: Profile = STORAGE.profiles.load(profile_id)
    return profile.workbooks.load(workbook_id).sources


def _serialize_source(source: Source) -> dict[str, Any]:
    data = source.data
    return {
        "id": data["id"],
        "name": data["name"],
        "description": data.get("description", ""),
        "folder": data.get("folder", ""),
        "kind": data.get("kind", "local"),
        "source_url": data.get("source_url"),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def list_sources(profile_id: int, workbook_id: int) -> list[dict[str, Any]]:
    return [_serialize_source(source) for source in _sources(profile_id, workbook_id).list()]


def add_file_source(
    profile_id: int, workbook_id: int, name: str, description: str, content: bytes, folder: str = ""
) -> dict[str, Any]:
    if not content:
        raise ValueError("Choose a non-empty file")
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError("Files must be 10 MB or smaller")
    source = _sources(profile_id, workbook_id).add_content(name, description, content, folder=normalize_folder(folder))
    return _serialize_source(source)


def add_content_source(
    profile_id: int, workbook_id: int, name: str, description: str, content: str, folder: str = ""
) -> dict[str, Any]:
    source = _sources(profile_id, workbook_id).add_content(name, description, content, folder=normalize_folder(folder))
    return _serialize_source(source)


def add_url_source(
    profile_id: int,
    workbook_id: int,
    name: str,
    description: str,
    url: str,
    download: bool,
    folder: str = "",
) -> dict[str, Any]:
    source = _sources(profile_id, workbook_id).add_url(name, description, url, download, normalize_folder(folder))
    return _serialize_source(source)


def update_source(
    profile_id: int, workbook_id: int, source_id: int, updates: dict[str, Any]
) -> dict[str, Any]:
    sources = _sources(profile_id, workbook_id)
    source = sources.load(source_id)
    if "folder" in updates:
        updates["folder"] = normalize_folder(updates["folder"])
        if updates["folder"] != source.folder:
            source.set_folder(updates["folder"])
    if updates.get("name") is not None:
        source.rename(updates["name"])
    if updates.get("description") is not None:
        source.redescribe(updates["description"])
    return _serialize_source(source)


def read_source(
    profile_id: int, workbook_id: int, source_id: int
) -> dict[str, Any]:
    source = _sources(profile_id, workbook_id).load(source_id)
    content = source.read()
    if isinstance(content, bytes):
        raw = content[: MAX_PREVIEW_BYTES + 1]
        text = raw.decode("utf-8", errors="replace")
    else:
        raw = content.encode("utf-8")[: MAX_PREVIEW_BYTES + 1]
        text = raw.decode("utf-8", errors="replace")
    truncated = len(raw) > MAX_PREVIEW_BYTES
    if truncated:
        text = text[:MAX_PREVIEW_BYTES] + "\n\n[Preview truncated]"
    return {"id": source.id, "name": source.name, "content": text, "truncated": truncated}


def redownload_source(profile_id: int, workbook_id: int, source_id: int) -> dict[str, Any]:
    source = _sources(profile_id, workbook_id).load(source_id)
    url = source.data.get("source_url")
    if not url:
        raise ValueError("Only URL sources can be downloaded again")
    with urlopen(url, timeout=30) as response:
        content = response.read(MAX_SOURCE_BYTES + 1)
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError("Downloaded files must be 10 MB or smaller")
    source.write(content)
    return _serialize_source(source)


def delete_source(profile_id: int, workbook_id: int, source_id: int) -> None:
    _sources(profile_id, workbook_id).delete(source_id)
