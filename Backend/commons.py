"""Shared backend dependencies and application-wide state."""

from pathlib import Path

from Pawm.STORAGE import Storage

STORAGE = Storage(Path(__file__).resolve().parents[1] / "Storage")


def normalize_folder(folder: str) -> str:
	if "\0" in folder:
		raise ValueError("Folder names cannot contain null characters")
	parts = [part.strip() for part in folder.replace("\\", "/").split("/") if part.strip()]
	if any(part in {".", ".."} for part in parts):
		raise ValueError("Folder paths cannot contain '.' or '..' segments")
	normalized = "/".join(parts)
	if len(normalized) > 1024:
		raise ValueError("Folder paths must be 1024 characters or shorter")
	return normalized
