"""Public entry point for the PAWM storage API."""

from __future__ import annotations

from pathlib import Path

from .Core import Core, initialize_storage
from .Manage_ApiKeys import ApiKey, WBApiKeys
from .Manage_Caller import Caller, WBCallers
from .Manage_Output import Output, WBOutputs
from .Manage_Profile import Profile, ProfilesManager
from .Manage_Source import Source, WBSources
from .Manage_Tool import Tool, WBToolPackager
from .Manage_Workbook import WBChat, WBConfig, WBManager, Workbook


class Storage:
    """Root object for PAWM storage, profiles, and profile data."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = initialize_storage(base_dir)
        self.core = Core(self.base_dir)
        self.profiles = ProfilesManager(self.base_dir)


__all__ = [
    "ApiKey",
    "Caller",
    "Core",
    "Output",
    "Profile",
    "ProfilesManager",
    "Source",
    "Storage",
    "Tool",
    "WBApiKeys",
    "WBCallers",
    "WBChat",
    "WBConfig",
    "WBManager",
    "WBOutputs",
    "WBSources",
    "WBToolPackager",
    "Workbook",
    "initialize_storage",
]
