"""Profile-scoped tool CRUD and secure ZIP package validation."""

from __future__ import annotations

import json
import os
import stat
import shutil
import zipfile
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

from Pawm.Core import Core
from Pawm.Manage_Profile import Profile
from Pawm.Manage_Tool import Tool

from ..commons import STORAGE

MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_BYTES = 25 * 1024 * 1024
REQUIRED_FILES = {"main.py", "README.md", "schema.json"}


def _profile(profile_id: int) -> Profile:
    return STORAGE.profiles.load(profile_id)


def _serialize_tool(tool: Tool) -> dict[str, Any]:
    data = tool.data
    return {
        "id": data["id"],
        "title": data["title"],
        "description": data.get("description", ""),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def _extract_package(archive_bytes: bytes) -> tuple[str, dict[str, Any], dict[str, bytes]]:
    if not archive_bytes:
        raise ValueError("Upload a non-empty ZIP package")
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP package must be 10 MB or smaller")

    try:
        archive = zipfile.ZipFile(BytesIO(archive_bytes))
    except (zipfile.BadZipFile, OSError) as error:
        raise ValueError("Upload must be a valid ZIP archive") from error

    with archive:
        entries: list[tuple[zipfile.ZipInfo, str]] = []
        extracted_size = 0
        for info in archive.infolist():
            normalized = info.filename.replace("\\", "/")
            path = PurePosixPath(normalized)
            if path.is_absolute() or any(part in ("..", "") for part in path.parts):
                raise ValueError("ZIP contains an unsafe file path")
            if path.parts and ":" in path.parts[0]:
                raise ValueError("ZIP contains an unsafe file path")
            if info.is_dir():
                continue
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("ZIP symbolic links are not allowed")
            extracted_size += info.file_size
            if extracted_size > MAX_EXTRACTED_BYTES:
                raise ValueError("Uncompressed ZIP content must be 25 MB or smaller")
            entries.append((info, path.as_posix()))

        first_parts = {PurePosixPath(name).parts[0] for _, name in entries if PurePosixPath(name).parts}
        if entries and len(first_parts) == 1 and all(
            len(PurePosixPath(name).parts) > 1 for _, name in entries
        ):
            root_directory = next(iter(first_parts))
            entries = [
                (info, PurePosixPath(name).relative_to(root_directory).as_posix())
                for info, name in entries
            ]

        files: dict[str, bytes] = {}
        for info, name in entries:
            if name in files:
                raise ValueError(f"ZIP contains duplicate path {name!r}")
            files[name] = archive.read(info)

    missing = REQUIRED_FILES - files.keys()
    if missing:
        raise ValueError(f"ZIP must contain: {', '.join(sorted(missing))}")
    for required in REQUIRED_FILES:
        if not files[required].strip():
            raise ValueError(f"ZIP file {required} must not be empty")

    try:
        schema = json.loads(files["schema.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("schema.json must contain valid JSON") from error
    if not isinstance(schema, (dict, list)) or not schema:
        raise ValueError("schema.json must contain a non-empty JSON object or array")

    try:
        main_source = files["main.py"].decode("utf-8")
        files["README.md"].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("main.py and README.md must be UTF-8 text") from error

    extra_files = {name: content for name, content in files.items() if name not in REQUIRED_FILES}
    return main_source, schema, {**extra_files, "README.md": files["README.md"]}


def list_tools(profile_id: int) -> list[dict[str, Any]]:
    return [_serialize_tool(item) for item in _profile(profile_id).tools.list()]


def create_tool(
    profile_id: int, title: str, description: str, archive_bytes: bytes
) -> dict[str, Any]:
    main_source, schema, package_files = _extract_package(archive_bytes)
    tool = _profile(profile_id).tools.add(
        title=title,
        description=description,
        content=main_source,
        schema=schema,
        files=package_files,
    )
    return _serialize_tool(tool)


def get_tool(profile_id: int, tool_id: int) -> dict[str, Any]:
    return _serialize_tool(_profile(profile_id).tools.load(tool_id))


def update_tool(profile_id: int, tool_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    profile = _profile(profile_id)
    package = updates.pop("package", None)
    if package is None:
        tool = profile.tools.update(tool_id, updates)
        return _serialize_tool(tool)

    main_source, schema, package_files = _extract_package(package)
    manager = profile.tools
    current = manager.load(tool_id)
    final_title = updates.get("title", current.title)
    final_description = updates.get("description", current.description)
    tools_directory = manager.folder
    directory = tools_directory / str(tool_id)
    staging = tools_directory / f".{tool_id}.staging"
    backup = tools_directory / f".{tool_id}.backup"

    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        staged_core = Core(staging)
        staged_core.write_file("main.py", main_source)
        staged_core.write_json("schema.json", schema)
        for filename, content in package_files.items():
            staged_core.write_file(filename, content)
        staged_core.write_json(
            "meta.json",
            {"id": tool_id, "title": final_title, "description": final_description},
        )

        tool = manager.update(tool_id, updates)
        shutil.rmtree(backup, ignore_errors=True)
        os.replace(directory, backup)
        try:
            os.replace(staging, directory)
        except BaseException:
            os.replace(backup, directory)
            raise
        shutil.rmtree(backup, ignore_errors=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return _serialize_tool(tool)


def delete_tool(profile_id: int, tool_id: int) -> None:
    _profile(profile_id).tools.delete(tool_id)
