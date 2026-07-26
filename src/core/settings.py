"""Persistent user preferences for Verto (local JSON only — no network)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from core.storage import SaveDestination
from utils.paths import config_dir

logger = logging.getLogger("verto.core.settings")

SETTINGS_FILE = "settings.json"
MAX_FILE_WARN_BYTES = 100 * 1024 * 1024  # 100 MiB


@dataclass
class AppSettings:
    """User-configurable Verto preferences."""

    save_destination: str = SaveDestination.DOWNLOADS.value
    custom_save_dir: str = ""
    theme: str = "forge"  # "forge" (dark) | "daylight"
    warn_large_files: bool = True
    large_file_threshold_mb: int = 100

    @property
    def destination_enum(self) -> SaveDestination:
        try:
            return SaveDestination(self.save_destination)
        except ValueError:
            return SaveDestination.DOWNLOADS

    @property
    def large_file_threshold_bytes(self) -> int:
        return max(1, int(self.large_file_threshold_mb)) * 1024 * 1024


def settings_path() -> Path:
    return config_dir() / SETTINGS_FILE


def load_settings() -> AppSettings:
    path = settings_path()
    if not path.is_file():
        return AppSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AppSettings()
        known = set(AppSettings.__dataclass_fields__)
        filtered = {k: v for k, v in data.items() if k in known}
        return AppSettings(**filtered)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Could not load settings (%s); using defaults", exc)
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    path = settings_path()
    try:
        path.write_text(
            json.dumps(asdict(settings), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not save settings: %s", exc)
