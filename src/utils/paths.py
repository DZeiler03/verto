"""Cross-platform path helpers for Verto cache, logs, and downloads."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


APP_NAME = "verto"


def _home() -> Path:
    return Path.home()


def cache_dir() -> Path:
    """Return the app cache root (creates it if missing)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
        path = base / APP_NAME
    elif sys.platform == "darwin":
        path = _home() / "Library" / "Caches" / APP_NAME
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        path = Path(xdg) / APP_NAME if xdg else _home() / ".cache" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def staging_dir() -> Path:
    """Hidden staging area for conversion outputs before 'Download'."""
    path = cache_dir() / "staging"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = cache_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or _home() / "AppData" / "Roaming")
        path = base / APP_NAME
    elif sys.platform == "darwin":
        path = _home() / "Library" / "Application Support" / APP_NAME
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        path = Path(xdg) / APP_NAME if xdg else _home() / ".config" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def downloads_dir() -> Path:
    """Best-effort OS Downloads folder."""
    if sys.platform == "win32":
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            candidate = Path(userprofile) / "Downloads"
            if candidate.is_dir():
                return candidate
    xdg_download = os.environ.get("XDG_DOWNLOAD_DIR")
    if xdg_download:
        p = Path(xdg_download).expanduser()
        if p.is_dir():
            return p
    for name in ("Downloads", "downloads", "Herunterladen"):
        candidate = _home() / name
        if candidate.is_dir():
            return candidate
    return _home()


def default_output_path(source: Path, target_ext: str) -> Path:
    """Suggest an output path in Downloads (or next to source if Downloads fails)."""
    ext = target_ext if target_ext.startswith(".") else f".{target_ext}"
    stem = source.stem
    name = f"{stem}{ext.lower()}"
    dest_dir = downloads_dir()
    candidate = dest_dir / name
    if not candidate.exists():
        return candidate
    n = 1
    while True:
        candidate = dest_dir / f"{stem}_{n}{ext.lower()}"
        if not candidate.exists():
            return candidate
        n += 1
