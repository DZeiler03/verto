"""Base types for the Morphix conversion engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ErrorCode(str, Enum):
    UNSUPPORTED = "unsupported"
    GOOGLE_POINTER = "google_pointer"
    CORRUPT = "corrupt"
    MISSING_DEPENDENCY = "missing_dependency"
    IO_ERROR = "io_error"
    TIMEOUT = "timeout"
    EMPTY = "empty"
    INTERNAL = "internal"


@dataclass
class ConversionError(Exception):
    """Structured conversion failure safe to show in the UI."""

    user_message: str
    technical_detail: str = ""
    code: ErrorCode = ErrorCode.INTERNAL

    def __str__(self) -> str:
        if self.technical_detail:
            return f"{self.user_message} ({self.technical_detail})"
        return self.user_message


@dataclass
class ConversionResult:
    """Successful conversion outcome."""

    output_path: Path
    source_path: Path
    target_format: str
    extra_outputs: list[Path] = field(default_factory=list)
    message: str = ""

    @property
    def all_outputs(self) -> list[Path]:
        paths = [self.output_path]
        paths.extend(self.extra_outputs)
        return paths


class BaseConverter(ABC):
    """Strategy interface implemented by Morphix converters."""

    name: str = "base"

    # Normalized lowercase extensions without leading dots, e.g. "png", "docx"
    input_formats: set[str] = set()
    output_formats: set[str] = set()

    def can_convert(self, source_format: str, target_format: str) -> bool:
        src = _norm_ext(source_format)
        dst = _norm_ext(target_format)
        if src == dst:
            return False
        return src in self.input_formats and dst in self.output_formats

    def list_targets(self, source_format: str) -> list[str]:
        src = _norm_ext(source_format)
        if src not in self.input_formats:
            return []
        return sorted(fmt for fmt in self.output_formats if fmt != src)

    @abstractmethod
    def convert(
        self,
        source: Path,
        target_format: str,
        output_path: Path,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        """Perform the conversion. Raises ConversionError on failure."""


def _norm_ext(ext: str) -> str:
    e = ext.lower().strip()
    if e.startswith("."):
        e = e[1:]
    return e


def normalize_format(ext: str) -> str:
    """Public alias for extension normalization."""
    return _norm_ext(ext)


def output_extension(target_format: str) -> str:
    """Map forge target keys (including Morphix special ops) to a real file extension."""
    t = normalize_format(target_format)
    special = {
        "pdf-compressed": "pdf",
        "compressed-pdf": "pdf",
        "pdf-split": "pdf",
        "split-pdf": "pdf",
        "ocr-txt": "txt",
        "ocr_txt": "txt",
        "ocr": "txt",
        "jpeg": "jpg",
        "tif": "tiff",
    }
    return special.get(t, t)


# User-facing message for Google Drive pointer files (hard requirement).
GOOGLE_POINTER_MESSAGE = (
    "This is a Google Drive link file, not a document — please export it from "
    "Google Drive as DOCX/XLSX/PPTX/ODT/PDF first, then convert that file."
)
