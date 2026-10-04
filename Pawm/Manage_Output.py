"""Workbook output records and content files."""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

from .Core import Core, Record, RecordManager, normalize_folder, split_file_path

_PATH_MIGRATION_LOCK = RLock()


class Output(Record):
    def read(self) -> str | bytes:
        content = Path(self._data["storage_path"]).read_bytes()
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content

    def write(self, content: str | bytes) -> None:
        Core(Path(self.storage_path).parent).write_file(self.storage_path, content)
        self._refresh()

    def rename(self, new_name: str) -> "Output":
        folder, name = split_file_path(new_name, self.data.get("folder", ""))
        self._move(folder, name)
        return self

    def redescribe(self, new_description: str) -> "Output":
        return self._refresh(description=new_description)

    def set_folder(self, folder: str) -> "Output":
        self._move(normalize_folder(folder), self.name)
        return self

    def _move(self, folder: str, name: str) -> None:
        updates: dict[str, Any] = {"folder": folder, "name": name}
        stored_path = self._data.get("storage_path")
        previous = Path(stored_path) if stored_path else None
        target = self._manager.path_for(self.id, name, folder)
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
            if moved:
                target.replace(previous)
            raise

    def _refresh(self, **updates: Any) -> "Output":
        updated = self._manager.update(self.id, updates)
        object.__setattr__(self, "_data", updated._data)
        return self


class WBOutputs(RecordManager[Output]):
    object_type = Output

    def __init__(self, workbook_path: str | Path) -> None:
        self.workbook_path = Path(workbook_path)
        self.folder = self.workbook_path / "Outputs"
        self.folder.mkdir(parents=True, exist_ok=True)
        super().__init__(self.workbook_path / "outputs.json")

    def path_for(self, identifier: Any, name: str = "item", folder: str = "") -> Path:
        normalized_folder, filename = split_file_path(name, folder)
        return self.folder.joinpath(*normalized_folder.split("/"), filename) if normalized_folder else self.folder / filename

    def _migrate_path(self, output: Output) -> Output:
        with _PATH_MIGRATION_LOCK:
            output = super().load(output.id)
            folder, name = split_file_path(output.name, output.data.get("folder", ""))
            target = self.path_for(output.id, name, folder)
            stored = output.data.get("storage_path")
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
            if folder != output.data.get("folder", ""):
                updates["folder"] = folder
            if name != output.name:
                updates["name"] = name
            if updates:
                try:
                    output = super().update(output.id, updates)
                except Exception:
                    if moved and previous is not None:
                        target.replace(previous)
                    raise
            return output

    def list(self) -> list[Output]:
        return [self._migrate_path(output) for output in super().list()]

    def load(self, identifier: Any) -> Output:
        return self._migrate_path(super().load(identifier))

    def add(self, name: str, description: str, content: str | bytes, folder: str = "") -> Output:
        folder, name = split_file_path(name, folder)
        path = self.path_for(0, name, folder)
        if path.exists():
            raise FileExistsError(f"A file already exists at {folder}/{name}".strip("/"))
        output = self.create(name=name, description=description, storage_path="", folder=folder)
        path = self.path_for(output.id, name, folder)
        Core(path.parent).write_file(path, content)
        return self.update(output.id, {"storage_path": str(path)})

    def update(
        self, identifier: Any, updates: dict[str, Any] | None = None, **fields: Any
    ) -> Output:
        changes = dict(updates or {})
        changes.update(fields)
        content = changes.pop("content", None)
        output = super().update(identifier, changes)
        if content is not None:
            Core(Path(output.storage_path).parent).write_file(output.storage_path, content)
            output = super().update(identifier, {})
        return output  # type: ignore[return-value]

    def delete(self, identifier: Any) -> None:
        output = self.load(identifier)
        stored = output.data.get("storage_path")
        if stored:
            target = Path(stored).resolve()
            try:
                target.relative_to(self.folder.resolve())
            except ValueError:
                pass
            else:
                target.unlink(missing_ok=True)
        super().delete(identifier)
