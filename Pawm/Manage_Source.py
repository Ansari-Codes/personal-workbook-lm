"""Workbook source records and file/link content management."""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from .Core import Core, Record, RecordManager, normalize_folder, split_file_path

_PATH_MIGRATION_LOCK = RLock()


def _read_content(path: Path) -> str | bytes:
    content = path.read_bytes()
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content


class Source(Record):
    def _content_path(self) -> Path | None:
        location = self._data.get("storage_path") or self._data.get("external_path")
        return Path(location) if location else None

    def read(self) -> str | bytes:
        path = self._content_path()
        if path is not None:
            return _read_content(path)
        url = self._data.get("source_url")
        if url:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read()
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content
        raise FileNotFoundError("This source has no readable content")

    def write(self, content: str | bytes) -> None:
        stored_path = self._data.get("storage_path")
        path = Path(stored_path) if stored_path else self._manager.path_for(
            self.id, self.name, self._data.get("folder", ""), self._data.get("kind", "local")
        )
        Core(path.parent).write_file(path, content)
        self._refresh(storage_path=str(path), external_path=None)

    def rename(self, new_name: str) -> "Source":
        folder, name = split_file_path(new_name, self._data.get("folder", ""))
        self._move(folder, name)
        return self

    def redescribe(self, new_description: str) -> "Source":
        return self._refresh(description=new_description)

    def set_folder(self, folder: str) -> "Source":
        self._move(normalize_folder(folder), self.name)
        return self

    def _move(self, folder: str, name: str) -> None:
        folder = normalize_folder(folder)
        updates: dict[str, Any] = {"folder": folder, "name": name}
        stored_path = self._data.get("storage_path")
        previous = Path(stored_path) if stored_path else None
        target = self._manager.path_for(self.id, name, folder, self._data.get("kind", "local"))
        moved = False
        if previous is not None:
            if previous.resolve() != target.resolve():
                if target.exists():
                    raise FileExistsError(f"A file already exists at {folder}/{name}".strip("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                if previous.exists():
                    previous.replace(target)
                    moved = True
            updates["storage_path"] = str(target)
        try:
            self._refresh(**updates)
        except Exception:
            if moved and previous is not None:
                target.replace(previous)
            raise

    def _refresh(self, **updates: Any) -> "Source":
        updated = self._manager.update(self.id, updates)
        object.__setattr__(self, "_data", updated._data)
        return self


class WBSources(RecordManager[Source]):
    object_type = Source

    def __init__(self, workbook_path: str | Path) -> None:
        self.workbook_path = Path(workbook_path)
        self.folder = self.workbook_path / "Sources"
        self.folder.mkdir(parents=True, exist_ok=True)
        super().__init__(self.workbook_path / "sources.json")

    def path_for(
        self, identifier: Any, name: str = "item", folder: str = "", kind: str = "local"
    ) -> Path:
        normalized_folder, filename = split_file_path(name, folder)
        return self.folder.joinpath(*normalized_folder.split("/"), filename) if normalized_folder else self.folder / filename

    @staticmethod
    def _category_folder(folder: str, kind: str) -> str:
        normalized = normalize_folder(folder)
        category = "Links" if kind == "link" else "Local"
        if normalized == category:
            return ""
        if normalized.startswith(f"{category}/"):
            return normalized[len(category) + 1:]
        return normalized

    def _migrate_path(self, source: Source) -> Source:
        with _PATH_MIGRATION_LOCK:
            source = super().load(source.id)
            kind = source.data.get("kind", "local")
            kind = source.data.get("kind", "local")
            folder, name = split_file_path(source.name, source.data.get("folder", ""))
            folder = self._category_folder(folder, kind)
            target = self.path_for(source.id, name, folder, kind)
            stored = source.data.get("storage_path")
            previous = Path(stored) if stored else None
            updates: dict[str, Any] = {}
            moved = False
            if previous is not None and previous.resolve() != target.resolve():
                if previous.exists():
                    if target.exists():
                        raise FileExistsError(f"A file already exists at {folder}/{name}".strip("/"))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    previous.replace(target)
                    moved = True
                updates["storage_path"] = str(target)
            if folder != source.data.get("folder", ""):
                updates["folder"] = folder
            if name != source.name:
                updates["name"] = name
            if updates:
                try:
                    source = super().update(source.id, updates)
                except Exception:
                    if moved and previous is not None:
                        target.replace(previous)
                    raise
            return source

    def list(self) -> list[Source]:
        return [self._migrate_path(source) for source in super().list()]

    def load(self, identifier: Any) -> Source:
        return self._migrate_path(super().load(identifier))

    def add_file(
        self, name: str, description: str, src: str | Path, copy: bool = True, folder: str = ""
    ) -> Source:
        folder, name = split_file_path(name, folder)
        folder = normalize_folder(folder)
        source_path = Path(src).expanduser().resolve()
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        fields: dict[str, Any] = {
            "name": name,
            "description": description,
            "kind": "local",
            "folder": folder,
        }
        if not copy:
            fields["external_path"] = str(source_path)
            return self.create(**fields)
        source = self.create(**fields)
        filename = name
        if not Path(filename).suffix and source_path.suffix:
            filename += source_path.suffix
        target = self.path_for(source.id, filename, folder, "local")
        if target.exists():
            self.delete(source.id)
            raise FileExistsError(f"A file already exists at {folder}/{filename}".strip("/"))
        shutil.copy2(source_path, target)
        return self.update(source.id, {"storage_path": str(target)})

    def add_url(
        self, name: str, description: str, src: str, download: bool = True, folder: str = ""
    ) -> Source:
        folder, name = split_file_path(name, folder)
        folder = normalize_folder(folder)
        if urlparse(src).scheme not in ("http", "https"):
            raise ValueError("src must be an http or https URL")
        source = self.create(
            name=name, description=description, kind="link", source_url=src, folder=folder
        )
        if not download:
            return source
        with urllib.request.urlopen(src, timeout=30) as response:
            content = response.read()
        suffix = Path(urlparse(src).path).suffix
        filename = name
        if not Path(filename).suffix:
            filename += suffix
        target = self.path_for(source.id, filename, folder, "link")
        if target.exists():
            self.delete(source.id)
            raise FileExistsError(f"A file already exists at {folder}/{filename}".strip("/"))
        Core(target.parent).write_file(target, content)
        return self.update(source.id, {"storage_path": str(target)})

    def add_content(
        self,
        name: str,
        description: str,
        content: str | bytes,
        encoding: str = "utf-8",
        folder: str = "",
    ) -> Source:
        folder, name = split_file_path(name, folder)
        folder = normalize_folder(folder)
        source = self.create(name=name, description=description, kind="local", folder=folder)
        target = self.path_for(source.id, name, folder, "local")
        if target.exists():
            self.delete(source.id)
            raise FileExistsError(f"A file already exists at {folder}/{name}".strip("/"))
        Core(target.parent).write_file(target, content, encoding)
        return self.update(source.id, {"storage_path": str(target)})

    def update(
        self, identifier: Any, updates: dict[str, Any] | None = None, **fields: Any
    ) -> Source:
        changes = dict(updates or {})
        changes.update(fields)
        return super().update(identifier, changes)  # type: ignore[return-value]

    def delete(self, identifier: Any) -> None:
        source = self.load(identifier)
        stored = source.data.get("storage_path")
        if stored:
            target = Path(stored).resolve()
            try:
                target.relative_to(self.folder.resolve())
            except ValueError:
                pass
            else:
                target.unlink(missing_ok=True)
        super().delete(identifier)
