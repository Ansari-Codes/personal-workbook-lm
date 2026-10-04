"""Workbook-scoped output CRUD and content operations."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from Pawm.Manage_Output import Output
from Pawm.Manage_Profile import Profile

from ..commons import STORAGE, normalize_folder

MAX_OUTPUT_BYTES = 50 * 1024 * 1024
TEXT_MEDIA_TYPES = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".py": "text/x-python",
    ".ts": "text/typescript",
    ".tsx": "text/tsx",
    ".vue": "text/x-vue",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
}


def _media_type(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return TEXT_MEDIA_TYPES.get(suffix) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def _outputs(profile_id: int, workbook_id: int):
    profile: Profile = STORAGE.profiles.load(profile_id)
    return profile.workbooks.load(workbook_id).outputs


def _serialize_output(output: Output) -> dict[str, Any]:
    data = output.data
    path = Path(data["storage_path"])
    return {
        "id": data["id"],
        "name": data["name"],
        "description": data.get("description", ""),
        "folder": data.get("folder", ""),
        "size": path.stat().st_size if path.is_file() else 0,
        "media_type": _media_type(data["name"]),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def list_outputs(profile_id: int, workbook_id: int) -> list[dict[str, Any]]:
    return [_serialize_output(output) for output in _outputs(profile_id, workbook_id).list()]


def create_output(
    profile_id: int, workbook_id: int, name: str, description: str, content: str, folder: str = ""
) -> dict[str, Any]:
    if len(content.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("Output files must be 50 MB or smaller")
    output = _outputs(profile_id, workbook_id).add(name, description, content, normalize_folder(folder))
    return _serialize_output(output)


def read_output(profile_id: int, workbook_id: int, output_id: int) -> dict[str, Any]:
    output = _outputs(profile_id, workbook_id).load(output_id)
    raw_content = Path(output.storage_path).read_bytes()
    media_type = _media_type(output.name)
    is_text_type = (
        media_type.startswith("text/")
        or media_type in {"application/json", "application/javascript", "application/x-sh", "application/xml"}
        or media_type.endswith("+xml")
    )
    if is_text_type or media_type == "application/octet-stream" and not Path(output.name).suffix:
        try:
            content: str | bytes = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_content
    else:
        content = raw_content
    return {
        **_serialize_output(output),
        "content": content if isinstance(content, str) else None,
        "content_base64": base64.b64encode(content).decode("ascii") if isinstance(content, bytes) else None,
        "encoding": "utf-8" if isinstance(content, str) else "base64",
    }


def update_output(
    profile_id: int, workbook_id: int, output_id: int, updates: dict[str, Any]
) -> dict[str, Any]:
    output = _outputs(profile_id, workbook_id).load(output_id)
    if "folder" in updates:
        updates["folder"] = normalize_folder(updates["folder"])
        output.set_folder(updates["folder"])
    if "name" in updates and updates["name"] != output.name:
        output.rename(updates["name"])
    if "description" in updates and updates["description"] != output.description:
        output.redescribe(updates["description"])
    if "content" in updates:
        output.write(updates["content"])
    return _serialize_output(output)


def replace_output_file(
    profile_id: int, workbook_id: int, output_id: int, content: bytes
) -> dict[str, Any]:
    if not content:
        raise ValueError("Output files must not be empty")
    if len(content) > MAX_OUTPUT_BYTES:
        raise ValueError("Output files must be 50 MB or smaller")
    output = _outputs(profile_id, workbook_id).load(output_id)
    output.write(content)
    return _serialize_output(output)


def delete_output(profile_id: int, workbook_id: int, output_id: int) -> None:
    _outputs(profile_id, workbook_id).delete(output_id)