"""MorphixEngine — orchestrates format detection and conversion for Verto."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.file_detector import FileDetector
from morphix.base import (
    BaseConverter,
    ConversionError,
    ConversionResult,
    ErrorCode,
    normalize_format,
)
from morphix.image_converter import ImageConverter
from morphix.pdf_converter import PdfConverter
from morphix.office_converter import OfficeConverter
from morphix.libreoffice import get_libreoffice
from morphix.pdf_tools import PdfTools
from morphix.ocr import OcrEngine, get_ocr

logger = logging.getLogger("verto.morphix.engine")


class MorphixEngine:
    """Verto's conversion engine (Morphix).

    Registers converters, resolves target formats, and runs conversions offline.
    Also exposes PDF tools (merge/split/compress) and optional Tesseract OCR.
    """

    def __init__(self, converters: list[BaseConverter] | None = None) -> None:
        self.detector = FileDetector()
        self._converters: list[BaseConverter] = converters or [
            ImageConverter(),
            PdfConverter(),
            OfficeConverter(),
        ]
        self.pdf_tools = PdfTools()
        self.ocr = get_ocr()

    @property
    def converters(self) -> list[BaseConverter]:
        return list(self._converters)

    def libreoffice_available(self) -> bool:
        return get_libreoffice().available()

    def ocr_available(self) -> bool:
        return self.ocr.available()

    def detect(self, source: Path | str):
        return self.detector.detect(source)

    def list_target_formats(self, source: Path | str) -> list[str]:
        """Return sorted unique target format extensions for *source*."""
        info = self.detector.detect(source)
        if info.is_google_pointer or not info.readable:
            return []
        if info.category.value == "unknown":
            return []

        src_fmt = info.format
        targets: set[str] = set()
        for conv in self._converters:
            for t in conv.list_targets(src_fmt):
                targets.add(normalize_format(t))

        # PDF tools (single-file pseudo-formats for the forge picker)
        if src_fmt == "pdf":
            targets.add("pdf-compressed")
            targets.add("pdf-split")
            if self.ocr_available():
                targets.add("ocr-txt")
        elif src_fmt in {"jpg", "png", "bmp", "webp", "tiff", "gif", "tif", "jpeg"}:
            if self.ocr_available():
                targets.add("ocr-txt")

        return sorted(targets)

    def can_convert(self, source: Path | str, target_format: str) -> bool:
        try:
            info = self.detector.ensure_convertible(source)
        except ConversionError:
            return False
        dst = normalize_format(target_format)
        return self._find_converter(info.format, dst) is not None

    def convert(
        self,
        source: Path | str,
        target_format: str,
        output_path: Path | str,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        """Convert *source* to *target_format*, writing to *output_path*.

        Raises ConversionError on failure (never crashes on bad input).
        """
        source = Path(source)
        output_path = Path(output_path)
        target = normalize_format(target_format)
        if target == "jpeg":
            target = "jpg"
        if target == "tif":
            target = "tiff"

        logger.info("Morphix convert: %s → %s", source, target)

        info = self.detector.ensure_convertible(source)
        src_fmt = info.format

        # Special Morphix operations (PDF tools + OCR)
        if target in {"pdf-compressed", "compressed-pdf"}:
            return self.compress_pdf(source, output_path.with_suffix(".pdf"), options)
        if target in {"pdf-split", "split-pdf"}:
            out_dir = output_path.parent / f"{source.stem}_pages"
            return self.split_pdf(source, out_dir)
        if target in {"ocr-txt", "ocr_txt", "ocr"}:
            return self.ocr_to_text(source, output_path.with_suffix(".txt"), options)

        if src_fmt == target:
            raise ConversionError(
                user_message="Source and target formats are the same.",
                code=ErrorCode.UNSUPPORTED,
            )

        converter = self._find_converter(src_fmt, target)
        if converter is None:
            raise ConversionError(
                user_message=f"No converter available for .{src_fmt} → .{target}.",
                technical_detail=f"source={source}",
                code=ErrorCode.UNSUPPORTED,
            )

        # Ensure sensible extension on output
        if output_path.suffix.lower().lstrip(".") not in {target, "jpeg" if target == "jpg" else target}:
            output_path = output_path.with_suffix(f".{target}")

        try:
            result = converter.convert(source, target, output_path, options or {})
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001 — Morphix must absorb unexpected errors
            logger.exception("Unexpected Morphix error")
            raise ConversionError(
                user_message="Conversion failed unexpectedly. See the log for details.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc

        logger.info("Morphix success: %s", result.output_path)
        return result

    def merge_pdfs(
        self,
        sources: list[Path | str],
        output_path: Path | str,
    ) -> ConversionResult:
        paths = [Path(p) for p in sources]
        return self.pdf_tools.merge(paths, Path(output_path))

    def split_pdf(
        self,
        source: Path | str,
        output_dir: Path | str,
    ) -> ConversionResult:
        return self.pdf_tools.split(Path(source), Path(output_dir))

    def compress_pdf(
        self,
        source: Path | str,
        output_path: Path | str,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        return self.pdf_tools.compress(Path(source), Path(output_path), options)

    def ocr_to_text(
        self,
        source: Path | str,
        output_path: Path | str,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        source = Path(source)
        output_path = Path(output_path)
        ext = normalize_format(source.suffix)
        if ext == "pdf":
            return self.ocr.ocr_pdf(source, output_path, options)
        if ext in {"jpg", "jpeg", "png", "bmp", "webp", "tiff", "tif", "gif"}:
            return self.ocr.ocr_image(source, output_path, options)
        raise ConversionError(
            user_message="OCR supports PDF and common image formats only.",
            code=ErrorCode.UNSUPPORTED,
        )

    def _find_converter(self, source_format: str, target_format: str) -> BaseConverter | None:
        src = normalize_format(source_format)
        dst = normalize_format(target_format)
        for conv in self._converters:
            if conv.can_convert(src, dst):
                return conv
        return None
