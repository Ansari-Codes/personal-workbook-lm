"""Workbook, chat, and configuration managers."""

from __future__ import annotations

import shutil
from pathlib import Path
from threading import Lock, RLock
from typing import Any

from .Core import Core, Record, RecordManager, timestamp

_CHAT_LOCKS: dict[Path, RLock] = {}
_CHAT_LOCKS_GUARD = Lock()


def _chat_lock(path: Path) -> RLock:
    normalized = path.resolve()
    with _CHAT_LOCKS_GUARD:
        return _CHAT_LOCKS.setdefault(normalized, RLock())


class Workbook(Record):
    @property
    def path(self) -> Path:
        return self._manager.path_for(self.id)

    @property
    def chat(self) -> "WBChat":
        return WBChat(self.path / "chat.json")

    @property
    def config(self) -> "WBConfig":
        return WBConfig(self.path / "config.json")

    @property
    def sources(self):
        from .Manage_Source import WBSources

        return WBSources(self.path)

    @property
    def outputs(self):
        from .Manage_Output import WBOutputs

        return WBOutputs(self.path)

    @property
    def callers(self):
        from .Manage_Caller import WBCallers

        return WBCallers(self._manager.profile_path)

    @property
    def api_keys(self):
        from .Manage_ApiKeys import WBApiKeys

        return WBApiKeys(self._manager.profile_path)

    @property
    def tools(self):
        from .Manage_Tool import WBToolPackager

        return WBToolPackager(self._manager.profile_path)


class WBManager(RecordManager[Workbook]):
    object_type = Workbook
    unique_fields = ("title", "description")

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)
        super().__init__(self.profile_path / "workbooks.json")

    def path_for(self, identifier: Any) -> Path:
        return self.profile_path / "Workbooks" / str(identifier)

    def create(self, title: str, description: str = "", **metadata: Any) -> Workbook:
        workbook = super().create(title=title, description=description, **metadata)
        path = self.path_for(workbook.id)
        (path / "Sources").mkdir(parents=True, exist_ok=True)
        (path / "Outputs").mkdir(parents=True, exist_ok=True)
        core = Core(path)
        core.write_json("sources.json", [])
        core.write_json("outputs.json", [])
        core.write_json("chat.json", [])
        core.write_json("config.json", {})
        return workbook

    def delete(self, identifier: Any) -> None:
        directory = self.path_for(identifier)
        super().delete(identifier)
        shutil.rmtree(directory, ignore_errors=True)


class WBChat:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.core = Core(self.path.parent)
        self._lock = _chat_lock(self.path)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return self.core.read_json(self.path, [])

    def add(self, msg_type: str, content: str, meta: dict[str, Any] | None = None) -> None:
        self.add_many([{"role": msg_type, "content": content, "meta": meta or {}}])

    def add_many(self, entries: list[dict[str, Any]]) -> None:
        with self._lock:
            messages = self.core.read_json(self.path, [])
            for entry in entries:
                now = timestamp()
                messages.append({
                    "role": entry["role"],
                    "content": entry["content"],
                    "meta": entry.get("meta", {}),
                    "created_at": now,
                    "updated_at": now,
                })
            self.core.write_json(self.path, messages)

    def clear(self) -> None:
        with self._lock:
            self.core.write_json(self.path, [])


class WBConfig:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.core = Core(self.path.parent)

    def all(self) -> dict[str, Any]:
        data = self.core.read_json(self.path, {})
        if not isinstance(data, dict):
            raise ValueError(f"Expected a JSON object in {self.path}")
        return data

    def get(self, key: str, default: Any = None) -> Any:
        return self.all().get(key, default)

    def set(self, key: str, value: Any) -> None:
        values = self.all()
        values[key] = value
        self.core.write_json(self.path, values)
