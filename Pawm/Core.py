"""Shared filesystem, JSON, and record primitives for PAWM storage."""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Generic, TypeVar


RecordType = TypeVar("RecordType", bound="Record")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_filename(value: str, fallback: str = "item") -> str:
    name = Path(str(value).replace("\\", "/")).name.strip().strip(".")
    return name or fallback


def normalize_folder(folder: str) -> str:
    value = str(folder).replace("\\", "/")
    if value.startswith("/") or (len(value) > 1 and value[1] == ":") or "\0" in value:
        raise ValueError("Folder paths must be relative")
    parts = [part.strip() for part in value.split("/") if part.strip()]
    if any(part in {".", ".."} for part in parts):
        raise ValueError("Folder paths cannot contain '.' or '..' segments")
    if any(_invalid_path_segment(part) for part in parts):
        raise ValueError("Folder names contain characters that are not valid on Windows")
    normalized = "/".join(parts)
    if len(normalized) > 1024:
        raise ValueError("Folder paths must be 1024 characters or shorter")
    return normalized


def split_file_path(name: str, folder: str = "") -> tuple[str, str]:
    value = str(name).replace("\\", "/")
    if value.startswith("/") or (len(value) > 1 and value[1] == ":") or "\0" in value:
        raise ValueError("File paths must be relative")
    parts = [part.strip() for part in value.split("/") if part.strip()]
    if not parts or any(part in {".", ".."} for part in parts):
        raise ValueError("File paths must include a file name and cannot contain '.' or '..' segments")
    if any(_invalid_path_segment(part) for part in parts):
        raise ValueError("File names contain characters that are not valid on Windows")
    parent = normalize_folder(folder)
    nested = normalize_folder("/".join(parts[:-1]))
    target_folder = "/".join(part for part in (parent, nested) if part)
    return normalize_folder(target_folder), parts[-1]


def _invalid_path_segment(value: str) -> bool:
    return (
        not value
        or value.endswith((".", " "))
        or any(character in '<>:"|?*' or ord(character) < 32 for character in value)
    )


def initialize_storage(base_dir: str | Path | None = None) -> Path:
    """Create and return a storage root, defaulting to Documents/PAWM_DATA."""
    root = (
        Path(base_dir).expanduser()
        if base_dir is not None
        else Path.home() / "Documents" / "PAWM_DATA"
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "Profiles").mkdir(exist_ok=True)
    profiles_file = root / "profiles.json"
    if not profiles_file.exists():
        Core(root).write_json(profiles_file, [])
    return root.resolve()


class Core:
    """Rooted pathing and basic file operations for a PAWM storage tree."""

    def __init__(self, base_dir: str | Path) -> None:
        self.root = Path(base_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str | Path) -> Path:
        """Return a path under the configured root (absolute paths pass through)."""
        if len(parts) == 1 and Path(parts[0]).is_absolute():
            return Path(parts[0])
        return self.root.joinpath(*parts)

    def ensure_directory(self, *parts: str | Path) -> Path:
        directory = self.path(*parts)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def read_json(self, path: str | Path, default: Any = None) -> Any:
        target = self.path(path)
        if not target.exists():
            return default
        with target.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def write_json(self, path: str | Path, value: Any) -> Path:
        target = self.path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            for attempt in range(7):
                try:
                    os.replace(temporary, target)
                    break
                except PermissionError:
                    if attempt == 6:
                        raise
                    time.sleep(0.025 * (2 ** attempt))
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
        return target

    def read_file(self, path: str | Path, encoding: str | None = "utf-8") -> str | bytes:
        target = self.path(path)
        if encoding is None:
            return target.read_bytes()
        return target.read_text(encoding=encoding)

    def write_file(
        self, path: str | Path, content: str | bytes, encoding: str = "utf-8"
    ) -> Path:
        target = self.path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding=encoding)
        return target


class Record:
    """A persisted row whose changes are written through its manager."""

    def __init__(self, manager: "RecordManager", data: dict[str, Any]) -> None:
        object.__setattr__(self, "_manager", manager)
        object.__setattr__(self, "_data", dict(data))

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._data)

    @property
    def id(self) -> Any:
        return self._data.get("id")

    def update(self, **updates: Any) -> "Record":
        updated = self._manager.update(self.id, updates)
        object.__setattr__(self, "_data", updated._data)
        return self

    def delete(self) -> None:
        self._manager.delete(self.id)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        elif name in self._data and name != "id":
            self.update(**{name: value})
        else:
            object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"


class RecordManager(Generic[RecordType]):
    """CRUD operations for an integer-ID JSON record list."""

    object_type: type[RecordType] = Record
    unique_fields: tuple[str, ...] = ()
    ignore_empty_unique_fields: tuple[str, ...] = ()
    criteria_aliases: dict[str, str] = {}

    def __init__(self, records_path: str | Path) -> None:
        self.records_path = Path(records_path)
        self.records_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _records(self) -> list[dict[str, Any]]:
        data = Core(self.records_path.parent).read_json(self.records_path, [])
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise ValueError(f"Expected a JSON list of objects in {self.records_path}")
        return data

    def _save(self, records: list[dict[str, Any]]) -> None:
        Core(self.records_path.parent).write_json(self.records_path, records)

    def _make_object(self, data: dict[str, Any]) -> RecordType:
        return self.object_type(self, data)  # type: ignore[return-value]

    def list(self) -> list[RecordType]:
        with self._lock:
            return [self._make_object(row) for row in self._records()]

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().casefold()
        return value

    def exists(self, **criteria: Any) -> bool:
        """Return whether one record matches every supplied field criterion."""
        if not criteria:
            return False
        normalized = {
            self.criteria_aliases.get(key, key): self._normalize(value)
            for key, value in criteria.items()
        }
        with self._lock:
            return any(
                all(self._normalize(row.get(key)) == value for key, value in normalized.items())
                for row in self._records()
            )

    def _check_unique(
        self,
        records: list[dict[str, Any]],
        candidate: dict[str, Any],
        excluding_id: Any = None,
    ) -> None:
        for field in self.unique_fields:
            value = candidate.get(field)
            if field in self.ignore_empty_unique_fields and value in (None, ""):
                continue
            normalized = self._normalize(value)
            for row in records:
                if excluding_id is not None and str(row.get("id")) == str(excluding_id):
                    continue
                if normalized == self._normalize(row.get(field)):
                    raise ValueError(f"{field} must be unique: {value!r}")

    def load(self, identifier: Any) -> RecordType:
        with self._lock:
            for row in self._records():
                display_name = row.get("name", row.get("title", ""))
                if str(row.get("id")) == str(identifier) or str(display_name) == str(identifier):
                    return self._make_object(row)
        raise KeyError(f"No record {identifier!r} in {self.records_path}")

    def create(self, **fields: Any) -> RecordType:
        with self._lock:
            records = self._records()
            fields.pop("id", None)
            now = timestamp()
            row = {
                **fields,
                "id": max((int(item.get("id", 0)) for item in records), default=0) + 1,
                "created_at": now,
                "updated_at": now,
            }
            self._check_unique(records, row)
            records.append(row)
            self._save(records)
            return self._make_object(row)

    def update(self, identifier: Any, updates: dict[str, Any]) -> RecordType:
        if not isinstance(updates, dict):
            raise TypeError("updates must be a dictionary")
        if "id" in updates or "created_at" in updates:
            raise ValueError("id and created_at cannot be changed")
        with self._lock:
            records = self._records()
            for row in records:
                if str(row.get("id")) == str(identifier):
                    candidate = {**row, **updates}
                    self._check_unique(records, candidate, excluding_id=identifier)
                    row.update(updates)
                    row["updated_at"] = timestamp()
                    self._save(records)
                    return self._make_object(row)
        raise KeyError(f"No record {identifier!r} in {self.records_path}")

    def delete(self, identifier: Any) -> None:
        with self._lock:
            records = self._records()
            remaining = [row for row in records if str(row.get("id")) != str(identifier)]
            if len(remaining) == len(records):
                raise KeyError(f"No record {identifier!r} in {self.records_path}")
            self._save(remaining)
