"""File type detection for Morphix / Verto (offline only)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from morphix.base import GOOGLE_POINTER_MESSAGE, ErrorCode, ConversionError, normalize_format

logger = logging.getLogger("verto.core.file_detector")

GOOGLE_EXTENSIONS = frozenset({"gdoc", "gsheet", "gslides"})

IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "bmp", "webp", "tiff", "tif", "gif"})
PDF_EXTENSIONS = frozenset({"pdf"})
DOC_EXTENSIONS = frozenset({"docx", "odt", "doc"})
SHEET_EXTENSIONS = frozenset({"xlsx", "ods", "csv", "xls"})
SLIDE_EXTENSIONS = frozenset({"pptx", "odp", "ppt"})
TEXT_EXTENSIONS = frozenset({"txt", "md", "text"})


class FileCategory(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    TEXT = "text"
    GOOGLE_LINK = "google_link"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DetectedFile:
    path: Path
    extension: str
    category: FileCategory
    is_google_pointer: bool = False
    readable: bool = True
    detail: str = ""

    @property
    def format(self) -> str:
        """Normalized format key used by Morphix (jpeg → jpg, tif → tiff)."""
        ext = self.extension
        if ext == "jpeg":
            return "jpg"
        if ext == "tif":
            return "tiff"
        return ext


class FileDetector:
    """Detect file kind from extension and light content checks."""

    def detect(self, path: Path | str) -> DetectedFile:
        path = Path(path)
        ext = normalize_format(path.suffix) if path.suffix else ""

        if not path.exists():
            return DetectedFile(
                path=path,
                extension=ext,
                category=FileCategory.UNKNOWN,
                readable=False,
                detail="File does not exist",
            )

        if not path.is_file():
            return DetectedFile(
                path=path,
                extension=ext,
                category=FileCategory.UNKNOWN,
                readable=False,
                detail="Not a regular file",
            )

        if path.stat().st_size == 0:
            return DetectedFile(
                path=path,
                extension=ext,
                category=self._category_for_ext(ext),
                readable=False,
                detail="File is empty",
            )

        if ext in GOOGLE_EXTENSIONS or self._looks_like_google_pointer(path, ext):
            return DetectedFile(
                path=path,
                extension=ext or "gdoc",
                category=FileCategory.GOOGLE_LINK,
                is_google_pointer=True,
                readable=False,
                detail=GOOGLE_POINTER_MESSAGE,
            )

        category = self._category_for_ext(ext)
        readable, detail = self._probe_readable(path, category, ext)
        return DetectedFile(
            path=path,
            extension=ext,
            category=category,
            readable=readable,
            detail=detail,
        )

    def ensure_convertible(self, path: Path | str) -> DetectedFile:
        """Detect and raise ConversionError for Google pointers / unreadable files."""
        info = self.detect(path)
        if info.is_google_pointer:
            raise ConversionError(
                user_message=GOOGLE_POINTER_MESSAGE,
                technical_detail=str(info.path),
                code=ErrorCode.GOOGLE_POINTER,
            )
        if not info.readable:
            raise ConversionError(
                user_message=info.detail or "This file cannot be read.",
                technical_detail=str(info.path),
                code=ErrorCode.CORRUPT if "corrupt" in (info.detail or "").lower() else ErrorCode.EMPTY,
            )
        if info.category == FileCategory.UNKNOWN:
            raise ConversionError(
                user_message=f"Unsupported or unknown file type: .{info.extension or '?'}",
                technical_detail=str(info.path),
                code=ErrorCode.UNSUPPORTED,
            )
        return info

    def _category_for_ext(self, ext: str) -> FileCategory:
        if ext in IMAGE_EXTENSIONS:
            return FileCategory.IMAGE
        if ext in PDF_EXTENSIONS:
            return FileCategory.PDF
        if ext in DOC_EXTENSIONS:
            return FileCategory.DOCUMENT
        if ext in SHEET_EXTENSIONS:
            return FileCategory.SPREADSHEET
        if ext in SLIDE_EXTENSIONS:
            return FileCategory.PRESENTATION
        if ext in TEXT_EXTENSIONS:
            return FileCategory.TEXT
        if ext in GOOGLE_EXTENSIONS:
            return FileCategory.GOOGLE_LINK
        return FileCategory.UNKNOWN

    def _looks_like_google_pointer(self, path: Path, ext: str) -> bool:
        """Google Drive desktop 'files' are tiny JSON pointers."""
        try:
            size = path.stat().st_size
            if size > 8192:
                return False
            # Only sniff non-binary-looking extensions or unknown small text
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text.startswith("{"):
                return False
            data = json.loads(text)
            if not isinstance(data, dict):
                return False
            # Typical keys: url, doc_id, resource_id
            blob = json.dumps(data).lower()
            if "docs.google.com" in blob or "drive.google.com" in blob:
                return True
            if "doc_id" in data or "resource_id" in data:
                return True
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            return False
        return False

    def _probe_readable(
        self, path: Path, category: FileCategory, ext: str
    ) -> tuple[bool, str]:
        try:
            if category == FileCategory.IMAGE:
                from PIL import Image

                with Image.open(path) as img:
                    img.verify()
                return True, ""
            if category == FileCategory.PDF:
                import fitz

                doc = fitz.open(path)
                try:
                    if doc.is_encrypted and not doc.authenticate(""):
                        return False, "PDF is password-protected"
                    _ = len(doc)
                finally:
                    doc.close()
                return True, ""
            if category == FileCategory.SPREADSHEET and ext == "csv":
                path.read_bytes()[:64]
                return True, ""
            if category == FileCategory.SPREADSHEET and ext in {"xlsx", "xls"}:
                # light zip/ole check for xlsx
                header = path.read_bytes()[:4]
                if ext == "xlsx" and header[:2] != b"PK":
                    return False, "File appears corrupted (not a valid XLSX/ZIP)"
                return True, ""
            if category == FileCategory.DOCUMENT and ext == "docx":
                header = path.read_bytes()[:2]
                if header != b"PK":
                    return False, "File appears corrupted (not a valid DOCX/ZIP)"
                return True, ""
            if category == FileCategory.PRESENTATION and ext == "pptx":
                header = path.read_bytes()[:2]
                if header != b"PK":
                    return False, "File appears corrupted (not a valid PPTX/ZIP)"
                return True, ""
            if category == FileCategory.TEXT:
                path.read_text(encoding="utf-8", errors="replace")
                return True, ""
            # ODF and others: existence is enough for now; LO will validate
            return True, ""
        except Exception as exc:  # noqa: BLE001 — detection must never crash
            logger.debug("Probe failed for %s: %s", path, exc)
            return False, f"File appears corrupted or unreadable: {exc}"
