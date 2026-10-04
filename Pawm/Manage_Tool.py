"""Tool package files, metadata, schemas, and callable functions."""

from __future__ import annotations

import importlib.util
import json
import secrets
import shutil
import sys
from pathlib import Path
from typing import Any

from .Core import Core, Record, RecordManager, safe_filename


class Tool(Record):
    def make_call(
        self,
        fn_name: str,
        arguments: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        main_file = Path(self.path) / "main.py"
        module_name = f"pawm_tool_{self.id}_{secrets.token_hex(4)}"
        spec = importlib.util.spec_from_file_location(module_name, main_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load tool from {main_file}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            function = getattr(module, fn_name)
            if not callable(function):
                raise TypeError(f"{fn_name!r} is not callable")
            return function(**{**(arguments or {}), **(context or {})})
        finally:
            sys.modules.pop(module_name, None)

    def delete(self) -> None:
        self._manager.delete(self.id)


class WBToolPackager(RecordManager[Tool]):
    object_type = Tool
    unique_fields = ("title",)

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)
        self.folder = self.profile_path / "Tools"
        self.folder.mkdir(parents=True, exist_ok=True)
        super().__init__(self.profile_path / "tools.json")

    def add(
        self,
        title: str,
        description: str = "",
        content: str = "",
        schema: dict[str, Any] | list[Any] | None = None,
        files: dict[str, str | bytes] | None = None,
    ) -> Tool:
        tool = super().create(title=title, description=description, path="")
        directory = self.folder / str(tool.id)
        directory.mkdir(parents=True, exist_ok=True)
        core = Core(directory)
        core.write_file("main.py", content)
        for filename, file_content in (files or {}).items():
            relative = Path(filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Invalid tool package path: {filename!r}")
            core.write_file(relative, file_content)
        core.write_json("schema.json", schema or {})
        core.write_json(
            "meta.json",
            {"id": tool.id, "title": title, "description": description},
        )
        core.write_file("README.md", f"# {title}\n\n{description}\n")
        return self.update(tool.id, {"path": str(directory)})

    def load(self, identifier: Any) -> Tool:
        try:
            return super().load(identifier)
        except KeyError:
            for tool in self.list():
                if tool.title == str(identifier):
                    return tool
            raise

    def update(
        self, identifier: Any, updates: dict[str, Any] | None = None, **fields: Any
    ) -> Tool:
        changes = dict(updates or {})
        changes.update(fields)
        tool = super().update(identifier, changes)
        directory = Path(tool.path)
        if directory.exists():
            Core(directory).write_json(
                "meta.json",
                {"id": tool.id, "title": tool.title, "description": tool.description},
            )
        return tool  # type: ignore[return-value]

    def delete(self, identifier: Any) -> None:
        tool = self.load(identifier)
        directory = Path(tool.path)
        super().delete(tool.id)
        shutil.rmtree(directory, ignore_errors=True)

    def get_schema(self, identifier: Any = None) -> Any:
        if identifier is not None:
            return Core(Path(self.load(identifier).path)).read_json("schema.json", {})
        combined: dict[str, Any] = {}
        for tool in self.list():
            combined[str(tool.id)] = Core(Path(tool.path)).read_json("schema.json", {})
        Core(self.folder).write_json("schema.json", combined)
        return combined
