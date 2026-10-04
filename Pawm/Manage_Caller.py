"""Python caller scripts and invocation management."""

from __future__ import annotations

import ast
import importlib.util
import secrets
import sys
from pathlib import Path
from typing import Any

from .Core import Core, Record, RecordManager
from .CallerTypes import INVOKE_OUTPUT, MODEL_OUTPUT


def _validate_caller(content: str) -> None:
    if not isinstance(content, str):
        raise TypeError("caller content must be Python source text")
    tree = ast.parse(content)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for name in ("INVOKE", "MODEL"):
        function = functions.get(name)
        if (
            function is None
            or function.args.posonlyargs
            or function.args.args
            or function.args.kwonlyargs
            or function.args.vararg
            or function.args.kwarg is None
            or function.args.kwarg.arg != "kwargs"
        ):
            raise ValueError(f"caller source must define {name}(**kwargs)")


class Caller(Record):
    def _call_function(self, function_name: str, **kwargs: Any) -> Any:
        path = Path(self.path)
        module_name = f"pawm_caller_{self.id}_{secrets.token_hex(4)}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load caller from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            function = getattr(module, function_name, None)
            if not callable(function):
                raise AttributeError(f"{path} must define {function_name}(**kwargs)")
            return function(**kwargs)
        finally:
            sys.modules.pop(module_name, None)

    def INVOKE(self, **kwargs: Any) -> INVOKE_OUTPUT:
        return self._call_function("INVOKE", **kwargs)

    def MODEL(self, **kwargs: Any) -> MODEL_OUTPUT:
        return self._call_function("MODEL", **kwargs)

    def update(self, **updates: Any) -> "Caller":
        content = updates.pop("content", None)
        if content is not None:
            _validate_caller(content)
            Core(Path(self.path).parent).write_file(self.path, content)
        updated = self._manager.update(self.id, updates)
        object.__setattr__(self, "_data", updated._data)
        return self

    def delete(self) -> None:
        self._manager.delete(self.id)


class WBCallers(RecordManager[Caller]):
    object_type = Caller
    unique_fields = ("name",)

    def __init__(self, profile_path: str | Path) -> None:
        self.profile_path = Path(profile_path)
        self.folder = self.profile_path / "Callers"
        self.folder.mkdir(parents=True, exist_ok=True)
        super().__init__(self.profile_path / "callers.json")

    def add(self, name: str, description: str, content: str) -> Caller:
        _validate_caller(content)
        caller = self.create(name=name, description=description, path="")
        path = self.folder / f"caller_{caller.id}.py"
        Core(self.folder).write_file(path, content)
        return self.update(caller.id, {"path": str(path)})

    def update(
        self, identifier: Any, updates: dict[str, Any] | None = None, **fields: Any
    ) -> Caller:
        changes = dict(updates or {})
        changes.update(fields)
        content = changes.pop("content", None)
        if content is not None:
            _validate_caller(content)
            caller = self.load(identifier)
            Core(self.folder).write_file(caller.path, content)
        return super().update(identifier, changes)  # type: ignore[return-value]

    def delete(self, identifier: Any) -> None:
        caller = self.load(identifier)
        Path(caller.path).unlink(missing_ok=True)
        super().delete(identifier)
