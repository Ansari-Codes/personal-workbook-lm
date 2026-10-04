"""Profile-scoped API-key credential records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .Core import Record, RecordManager

class ApiKey(Record):
    def update(self, **updates: Any) -> "ApiKey":
        updated = self._manager.update(self.id, updates)
        object.__setattr__(self, "_data", updated._data)
        return self

    def delete(self) -> None:
        self._manager.delete(self.id)


class WBApiKeys(RecordManager[ApiKey]):
    object_type = ApiKey
    unique_fields = ("name",)

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)
        super().__init__(self.profile_path / "api_keys.json")
        records = self._records()
        migrated = []
        changed = False
        for record in records:
            current = {key: value for key, value in record.items() if key != "caller_id"}
            if len(current) != len(record):
                changed = True
            if "secret" not in current and "key" in current:
                current["secret"] = current.pop("key")
                changed = True
            if "base_url" not in current and "endpoint" in current:
                legacy_endpoint = str(current.pop("endpoint")).rstrip("/")
                chat_suffix = "/chat/completions"
                if legacy_endpoint.endswith(chat_suffix):
                    legacy_endpoint = legacy_endpoint[:-len(chat_suffix)]
                current["base_url"] = legacy_endpoint
                current["endpoints"] = {
                    "chat": "/chat/completions",
                    "models": "/models",
                }
                changed = True
            migrated.append(current)
        if changed or len(migrated) != len(records):
            self._save(migrated)

    def add(
        self,
        name: str,
        description: str,
        secret: str,
        base_url: str,
        endpoints: dict[str, str],
        meta: dict[str, Any] | None = None,
    ) -> ApiKey:
        return super().create(
            name=name,
            description=description,
            secret=secret,
            base_url=base_url,
            endpoints=endpoints,
            meta=meta or {},
        )  # type: ignore[return-value]

    def get(self, identifier: Any) -> ApiKey:
        return self.load(identifier)

    def update(
        self, identifier: Any, updates: dict[str, Any] | None = None, **fields: Any
    ) -> ApiKey:
        changes = dict(updates or {})
        changes.update(fields)
        if "caller_id" in changes:
            raise ValueError("API keys do not have a caller_id")
        return super().update(identifier, changes)  # type: ignore[return-value]
