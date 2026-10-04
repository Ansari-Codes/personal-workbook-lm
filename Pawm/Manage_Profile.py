"""Profile records and profile directory management."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .Core import Core, Record, RecordManager


class Profile(Record):
    @property
    def path(self) -> Path:
        return self._manager.path_for(self.id)

    @property
    def workbooks(self):
        from .Manage_Workbook import WBManager

        return WBManager(self.path)

    @property
    def callers(self):
        from .Manage_Caller import WBCallers

        return WBCallers(self.path)

    @property
    def api_keys(self):
        from .Manage_ApiKeys import WBApiKeys

        return WBApiKeys(self.path)

    @property
    def tools(self):
        from .Manage_Tool import WBToolPackager

        return WBToolPackager(self.path)

    def update(self, **updates: Any) -> "Profile":
        updated = self._manager.update(self.id, updates)
        object.__setattr__(self, "_data", updated._data)
        return self

    def delete(self) -> None:
        self._manager.delete(self.id)


class ProfilesManager(RecordManager[Profile]):
    object_type = Profile
    unique_fields = ("name",)
    criteria_aliases = {"username": "name"}

    def __init__(self, storage_root: str | Path) -> None:
        self.storage_root = Path(storage_root)
        super().__init__(self.storage_root / "profiles.json")

    def path_for(self, identifier: Any) -> Path:
        return self.storage_root / "Profiles" / str(identifier)

    def create(
        self,
        name: str,
        description: str = "",
        **metadata: Any,
    ) -> Profile:
        fields = {"name": name, "description": description, **metadata}
        profile = super().create(**fields)
        directory = self.path_for(profile.id)
        for child in ("Workbooks", "Callers", "Tools"):
            (directory / child).mkdir(parents=True, exist_ok=True)
        for filename in ("workbooks.json", "callers.json", "api_keys.json", "tools.json"):
            Core(directory).write_json(filename, [])
        return profile

    def delete(self, identifier: Any) -> None:
        directory = self.path_for(identifier)
        super().delete(identifier)
        shutil.rmtree(directory, ignore_errors=True)
