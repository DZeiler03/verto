"""Morphix offline OCR via local Tesseract (optional dependency).

No network. Requires the `tesseract` binary and optionally the `pytesseract` package.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from morphix.base import ConversionError, ConversionResult, ErrorCode

logger = logging.getLogger("verto.morphix.ocr")


class OcrEngine:
    """Run Tesseract locally on images or rendered PDF pages."""

    def available(self) -> bool:
        return shutil.which("tesseract") is not None

    def binary_path(self) -> str | None:
        return shutil.which("tesseract")

    def ocr_image(
        self,
        source: Path,
        output_path: Path,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        options = options or {}
        source = Path(source)
        output_path = Path(output_path)
        text = self._tesseract_image(source, lang=str(options.get("lang", "eng")))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        return ConversionResult(
            output_path=output_path,
            source_path=source,
            target_format="txt",
            message="OCR extracted text from image",
        )

    def ocr_pdf(
        self,
        source: Path,
        output_path: Path,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        """Render each PDF page and OCR → single text file."""
        options = options or {}
        source = Path(source)
        output_path = Path(output_path)
        if not self.available():
            raise ConversionError(
                user_message=(
                    "Tesseract OCR is not installed. On Linux: "
                    "sudo apt install tesseract-ocr  (or dnf/pacman equivalent)."
                ),
                code=ErrorCode.MISSING_DEPENDENCY,
            )

        try:
            import fitz
        except ImportError as exc:
            raise ConversionError(
                user_message="PyMuPDF is required for PDF OCR.",
                technical_detail=str(exc),
                code=ErrorCode.MISSING_DEPENDENCY,
            ) from exc

        dpi = int(options.get("dpi", 200))
        lang = str(options.get("lang", "eng"))
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        try:
            doc = fitz.open(source)
            parts: list[str] = []
            try:
                if doc.is_encrypted and not doc.authenticate(""):
                    raise ConversionError(
                        user_message="This PDF is password-protected.",
                        code=ErrorCode.CORRUPT,
                    )
                if doc.page_count == 0:
                    raise ConversionError(
                        user_message="PDF has no pages.",
                        code=ErrorCode.EMPTY,
                    )
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    # Write temp PNG next to output
                    tmp_png = output_path.parent / f".verto_ocr_p{i}.png"
                    try:
                        pix.save(str(tmp_png))
                        page_text = self._tesseract_image(tmp_png, lang=lang)
                        parts.append(f"--- Page {i + 1} ---\n{page_text.strip()}\n")
                    finally:
                        tmp_png.unlink(missing_ok=True)
            finally:
                doc.close()
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                user_message="OCR failed on this PDF.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(parts), encoding="utf-8")
        return ConversionResult(
            output_path=output_path,
            source_path=source,
            target_format="txt",
            message=f"OCR extracted text from {len(parts)} page(s)",
        )

    def _tesseract_image(self, image_path: Path, lang: str = "eng") -> str:
        if not self.available():
            raise ConversionError(
                user_message=(
                    "Tesseract OCR is not installed. On Linux: "
                    "sudo apt install tesseract-ocr"
                ),
                code=ErrorCode.MISSING_DEPENDENCY,
            )
        # Prefer pytesseract if present; else CLI
        try:
            import pytesseract
            from PIL import Image

            with Image.open(image_path) as img:
                return pytesseract.image_to_string(img, lang=lang)
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("pytesseract failed, trying CLI: %s", exc)

        import subprocess

        try:
            completed = subprocess.run(
                [
                    "tesseract",
                    str(image_path),
                    "stdout",
                    "-l",
                    lang,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConversionError(
                user_message="OCR timed out.",
                technical_detail=str(exc),
                code=ErrorCode.TIMEOUT,
            ) from exc
        except OSError as exc:
            raise ConversionError(
                user_message="Failed to start Tesseract.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc

        if completed.returncode != 0:
            raise ConversionError(
                user_message="Tesseract could not read this image.",
                technical_detail=(completed.stderr or "")[:400],
                code=ErrorCode.INTERNAL,
            )
        return completed.stdout or ""


_ocr = OcrEngine()


def get_ocr() -> OcrEngine:
    return _ocr
