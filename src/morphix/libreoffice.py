"""LibreOffice headless bridge used by Morphix for Office ⇄ PDF/ODF conversions.

All work is local subprocess only — no network.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from morphix.base import ConversionError, ErrorCode

logger = logging.getLogger("verto.morphix.libreoffice")

# Common install locations (in addition to PATH)
_CANDIDATES = (
    "soffice",
    "libreoffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)

_DEFAULT_TIMEOUT = 180  # seconds


class LibreOfficeBridge:
    """Discover and invoke local LibreOffice for format conversion."""

    def __init__(self) -> None:
        self._binary: str | None = None
        self._probed = False

    def available(self) -> bool:
        return self.binary_path() is not None

    def binary_path(self) -> str | None:
        if not self._probed:
            self._binary = self._find_binary()
            self._probed = True
        return self._binary

    def _find_binary(self) -> str | None:
        for candidate in _CANDIDATES:
            if os.path.sep in candidate or (os.path.altsep and os.path.altsep in candidate):
                if Path(candidate).is_file():
                    return candidate
            else:
                found = shutil.which(candidate)
                if found:
                    return found
        return None

    def convert(
        self,
        source: Path,
        target_ext: str,
        output_dir: Path | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> Path:
        """Convert *source* to *target_ext* via soffice --headless.

        Returns the path of the produced file inside *output_dir*.
        """
        binary = self.binary_path()
        if not binary:
            raise ConversionError(
                user_message=(
                    "LibreOffice is required for this conversion but was not found. "
                    "Install LibreOffice and ensure 'soffice' is on your PATH."
                ),
                technical_detail="soffice not found",
                code=ErrorCode.MISSING_DEPENDENCY,
            )

        source = source.resolve()
        if not source.is_file():
            raise ConversionError(
                user_message="Source file not found.",
                technical_detail=str(source),
                code=ErrorCode.IO_ERROR,
            )

        ext = target_ext.lower().lstrip(".")
        out_dir = Path(output_dir) if output_dir else source.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        # LibreOffice writes into --outdir using the source stem + new ext
        expected = out_dir / f"{source.stem}.{ext}"

        # Use a private profile dir so concurrent runs don't clash
        with tempfile.TemporaryDirectory(prefix="verto-lo-") as profile:
            cmd = [
                binary,
                "--headless",
                "--norestore",
                "--nolockcheck",
                f"-env:UserInstallation=file://{Path(profile).as_posix()}",
                "--convert-to",
                ext,
                "--outdir",
                str(out_dir),
                str(source),
            ]
            logger.info("LibreOffice convert: %s -> %s", source.name, ext)
            try:
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    env={**os.environ, "SAL_USE_VCLPLUGIN": "svp"},
                )
            except subprocess.TimeoutExpired as exc:
                raise ConversionError(
                    user_message="Conversion timed out. The file may be too large or complex.",
                    technical_detail=str(exc),
                    code=ErrorCode.TIMEOUT,
                ) from exc
            except OSError as exc:
                raise ConversionError(
                    user_message="Failed to start LibreOffice.",
                    technical_detail=str(exc),
                    code=ErrorCode.INTERNAL,
                ) from exc

            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "").strip()
                raise ConversionError(
                    user_message="LibreOffice could not convert this file.",
                    technical_detail=detail[:500] or f"exit {completed.returncode}",
                    code=ErrorCode.INTERNAL,
                )

        if not expected.is_file():
            # LO sometimes uses slightly different naming; search out_dir
            matches = list(out_dir.glob(f"{source.stem}*.{ext}"))
            if matches:
                return matches[0]
            raise ConversionError(
                user_message="LibreOffice finished but the output file was not found.",
                technical_detail=f"expected {expected}",
                code=ErrorCode.IO_ERROR,
            )
        return expected


# Module-level singleton for discovery caching
_bridge = LibreOfficeBridge()


def get_libreoffice() -> LibreOfficeBridge:
    return _bridge
