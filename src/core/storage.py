"""Staging cache and download/save destination logic for Verto.

Conversion results are written only to a private staging folder. Clicking
"Download" copies them to the user-facing destination (Downloads, next to
source, custom folder, or Save As).
"""

from __future__ import annotations

import logging
import shutil
import time
import uuid
from enum import Enum
from pathlib import Path

from utils.paths import downloads_dir, staging_dir

logger = logging.getLogger("verto.core.storage")

STALE_SECONDS = 24 * 60 * 60  # 24 hours


class SaveDestination(str, Enum):
    DOWNLOADS = "downloads"
    NEXT_TO_SOURCE = "next_to_source"
    ALWAYS_ASK = "always_ask"
    CUSTOM = "custom"


class StorageManager:
    """Manage Morphix output staging and user-facing 'download' saves."""

    def __init__(
        self,
        destination: SaveDestination = SaveDestination.DOWNLOADS,
        custom_dir: Path | None = None,
    ) -> None:
        self.destination = destination
        self.custom_dir = Path(custom_dir) if custom_dir else None
        self._staging = staging_dir()

    def apply_prefs(
        self,
        destination: SaveDestination,
        custom_dir: Path | str | None = None,
    ) -> None:
        self.destination = destination
        self.custom_dir = Path(custom_dir) if custom_dir else None

    @property
    def staging_root(self) -> Path:
        return self._staging

    def make_staging_path(self, target_format: str, stem: str | None = None) -> Path:
        """Allocate a unique path in the staging area for a conversion result."""
        ext = target_format if target_format.startswith(".") else f".{target_format}"
        name = stem or "forged"
        # Keep original stem readable for Download default names
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
        unique = f"{safe}_{uuid.uuid4().hex[:10]}{ext.lower()}"
        return self._staging / unique

    def resolve_save_path(
        self,
        source: Path,
        target_format: str,
        asked_path: Path | None = None,
        staged_name: str | None = None,
    ) -> Path:
        """Resolve final user-facing save path based on destination policy."""
        ext = target_format if target_format.startswith(".") else f".{target_format}"
        if staged_name:
            # Prefer original stem from source for user-facing name
            filename = f"{source.stem}{ext.lower()}"
        else:
            filename = f"{source.stem}{ext.lower()}"

        if self.destination == SaveDestination.ALWAYS_ASK:
            if asked_path is not None:
                return Path(asked_path)
            # Caller must prompt; return a Downloads suggestion as fallback
            return self._unique(downloads_dir() / filename)
        if self.destination == SaveDestination.NEXT_TO_SOURCE:
            return self._unique(source.parent / filename)
        if self.destination == SaveDestination.CUSTOM and self.custom_dir is not None:
            return self._unique(Path(self.custom_dir) / filename)
        return self._unique(downloads_dir() / filename)

    def needs_save_dialog(self) -> bool:
        return self.destination == SaveDestination.ALWAYS_ASK

    def promote(
        self,
        staged: Path,
        destination: Path,
        *,
        remove_staged: bool = False,
    ) -> Path:
        """Copy staged file to destination (Download action)."""
        staged = Path(staged)
        if not staged.is_file():
            raise FileNotFoundError(f"Staged file missing: {staged}")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination = self._unique(destination)
        shutil.copy2(staged, destination)
        logger.info("Promoted %s → %s", staged, destination)
        if remove_staged:
            try:
                staged.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Could not remove staged file after download: %s", exc)
        return destination

    def promote_all(
        self,
        staged_paths: list[Path],
        primary_destination: Path,
    ) -> list[Path]:
        """Promote primary + sibling extras into the destination folder."""
        saved: list[Path] = []
        dest_dir = primary_destination.parent
        for i, staged in enumerate(staged_paths):
            staged = Path(staged)
            if i == 0:
                dest = primary_destination
            else:
                dest = dest_dir / staged.name
                # Prefer source-like names for extras already named page_N
                dest = dest_dir / Path(staged.name).name
            saved.append(self.promote(staged, dest))
        return saved

    def cleanup_staging(self, older_than_seconds: float | None = None) -> int:
        """Delete staged files. If older_than is set, only those older than that."""
        removed = 0
        now = time.time()
        if not self._staging.is_dir():
            return 0
        for path in self._staging.iterdir():
            if not path.is_file():
                continue
            try:
                if older_than_seconds is not None:
                    age = now - path.stat().st_mtime
                    if age < older_than_seconds:
                        continue
                path.unlink(missing_ok=True)
                removed += 1
            except OSError as exc:
                logger.warning("Could not remove staged file %s: %s", path, exc)
        return removed

    def cleanup_stale_on_startup(self) -> int:
        return self.cleanup_staging(older_than_seconds=STALE_SECONDS)

    def cleanup_all_on_exit(self) -> int:
        return self.cleanup_staging(older_than_seconds=None)

    def destination_label(self) -> str:
        if self.destination == SaveDestination.DOWNLOADS:
            return f"Downloads ({downloads_dir()})"
        if self.destination == SaveDestination.NEXT_TO_SOURCE:
            return "Next to source file"
        if self.destination == SaveDestination.ALWAYS_ASK:
            return "Ask every time (Save As)"
        if self.destination == SaveDestination.CUSTOM:
            return str(self.custom_dir or "(not set)")
        return "Downloads"

    @staticmethod
    def _unique(path: Path) -> Path:
        if not path.exists():
            return path
        stem, suffix, parent = path.stem, path.suffix, path.parent
        n = 1
        while True:
            candidate = parent / f"{stem}_{n}{suffix}"
            if not candidate.exists():
                return candidate
            n += 1
