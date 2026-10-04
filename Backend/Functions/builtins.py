"""Import repository builtin callers and tools into a profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Pawm.Core import Core
from Pawm.Manage_Profile import Profile

BUILTIN_ROOT = Path(__file__).resolve().parents[2] / "Builtin"


def _registry(filename: str) -> list[dict[str, Any]]:
    manifest = BUILTIN_ROOT / filename
    records = json.loads(manifest.read_text(encoding="utf-8"))
    changed = False
    for record in records:
        path = Path(record["path"].replace("\\", "/"))
        relative_path = record.get("relative_path")
        if path.is_absolute() and not path.exists() and relative_path:
            path = Path(relative_path.replace("\\", "/"))
        if not path.is_absolute():
            record["relative_path"] = str(path).replace("\\", "/")
            path = BUILTIN_ROOT / path
        absolute_path = str(path.resolve())
        if record["path"] != absolute_path:
            record["path"] = absolute_path
            changed = True
    if changed:
        Core(BUILTIN_ROOT).write_json(manifest, records)
    return records


def ensure_profile_builtins(profile: Profile) -> tuple[int | None, list[int]]:
    """Copy missing builtins once and return the default caller and tool IDs."""
    default_caller_id: int | None = None
    callers = profile.callers.list()
    for item in _registry("callers.json"):
        builtin_id = f"caller:{item['id']}"
        caller = next((record for record in callers if record.data.get("builtin_id") == builtin_id), None)
        if caller is None:
            name = item["name"]
            if any(record.name == name for record in callers):
                name = f"{name} (built-in)"
            caller = profile.callers.add(
                name=name,
                description=item.get("description", ""),
                content=Path(item["path"]).read_text(encoding="utf-8"),
            )
            caller = profile.callers.update(caller.id, {"builtin_id": builtin_id})
            callers.append(caller)
        if default_caller_id is None:
            default_caller_id = caller.id

    tools = profile.tools.list()
    default_tool_ids: list[int] = []
    for item in _registry("tools.json"):
        builtin_id = f"tool:{item['id']}"
        tool = next((record for record in tools if record.data.get("builtin_id") == builtin_id), None)
        if tool is None:
            package = Path(item["path"])
            package_files = {
                path.relative_to(package).as_posix(): path.read_bytes()
                for path in package.rglob("*")
                if path.is_file() and path.name not in {"main.py", "schema.json", "meta.json"}
                and "__pycache__" not in path.parts
            }
            title = item["title"]
            existing_titles = {record.title.casefold() for record in tools}
            if title.casefold() in existing_titles:
                title = f"{title} (built-in)"
            tool = profile.tools.add(
                title=title,
                description=item.get("description", ""),
                content=(package / "main.py").read_text(encoding="utf-8"),
                schema=json.loads((package / "schema.json").read_text(encoding="utf-8")),
                files=package_files,
            )
            tool = profile.tools.update(tool.id, {
                "builtin_id": builtin_id,
                "requires_workbook": bool(item.get("requires_workbook", False)),
            })
            tools.append(tool)
        default_tool_ids.append(tool.id)

    return default_caller_id, default_tool_ids
