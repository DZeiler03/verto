"""Morphix PDF converter — PyMuPDF (fitz) for offline PDF read/write/render."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from morphix.base import (
    BaseConverter,
    ConversionError,
    ConversionResult,
    ErrorCode,
    normalize_format,
)

logger = logging.getLogger("verto.morphix.pdf")


class PdfConverter(BaseConverter):
    """PDF → images (per page), PDF → TXT, TXT → PDF."""

    name = "pdf"

    input_formats = {"pdf", "txt"}
    output_formats = {"png", "jpg", "txt", "pdf"}

    def can_convert(self, source_format: str, target_format: str) -> bool:
        src = normalize_format(source_format)
        dst = normalize_format(target_format)
        if dst == "jpeg":
            dst = "jpg"
        if src == "pdf" and dst in {"png", "jpg", "txt"}:
            return True
        if src == "txt" and dst == "pdf":
            return True
        return False

    def list_targets(self, source_format: str) -> list[str]:
        src = normalize_format(source_format)
        if src == "pdf":
            return ["jpg", "png", "txt"]
        if src == "txt":
            return ["pdf"]
        return []

    def convert(
        self,
        source: Path,
        target_format: str,
        output_path: Path,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        options = options or {}
        source = Path(source)
        output_path = Path(output_path)
        target = normalize_format(target_format)
        if target == "jpeg":
            target = "jpg"
        src_ext = normalize_format(source.suffix)

        if not source.is_file():
            raise ConversionError(
                user_message="Source file not found.",
                technical_detail=str(source),
                code=ErrorCode.IO_ERROR,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if src_ext == "pdf" and target in {"png", "jpg"}:
            return self._pdf_to_images(source, target, output_path, options)
        if src_ext == "pdf" and target == "txt":
            return self._pdf_to_txt(source, output_path)
        if src_ext == "txt" and target == "pdf":
            return self._txt_to_pdf(source, output_path)
        raise ConversionError(
            user_message=f"PDF converter cannot convert {src_ext} → {target}.",
            code=ErrorCode.UNSUPPORTED,
        )

    def _open_pdf(self, source: Path):
        try:
            import fitz
        except ImportError as exc:
            raise ConversionError(
                user_message="PyMuPDF is required for PDF conversion.",
                technical_detail=str(exc),
                code=ErrorCode.MISSING_DEPENDENCY,
            ) from exc
        try:
            doc = fitz.open(source)
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                user_message="Could not open PDF. The file may be corrupted.",
                technical_detail=str(exc),
                code=ErrorCode.CORRUPT,
            ) from exc
        if doc.is_encrypted and not doc.authenticate(""):
            doc.close()
            raise ConversionError(
                user_message="This PDF is password-protected and cannot be converted offline without the password.",
                code=ErrorCode.CORRUPT,
            )
        return doc

    def _pdf_to_images(
        self,
        source: Path,
        target: str,
        output_path: Path,
        options: dict[str, Any],
    ) -> ConversionResult:
        import fitz

        dpi = int(options.get("dpi", 150))
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        doc = self._open_pdf(source)
        extra: list[Path] = []
        primary: Path | None = None
        try:
            page_count = doc.page_count
            if page_count == 0:
                raise ConversionError(
                    user_message="PDF has no pages.",
                    code=ErrorCode.EMPTY,
                )

            # Single page → write directly to output_path
            # Multi-page → write page_1, page_2… next to output stem
            stem = output_path.stem
            parent = output_path.parent
            suffix = f".{target}"

            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                if page_count == 1:
                    out = output_path
                    if target == "jpg":
                        pix.save(str(out), output="jpg")
                    else:
                        pix.save(str(out))
                    primary = out
                else:
                    out = parent / f"{stem}_page{i + 1}{suffix}"
                    if target == "jpg":
                        pix.save(str(out), output="jpg")
                    else:
                        pix.save(str(out))
                    if i == 0:
                        primary = out
                    else:
                        extra.append(out)

        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("PDF→image failed")
            raise ConversionError(
                user_message="Failed to render PDF pages as images.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc
        finally:
            doc.close()

        if primary is None:
            raise ConversionError(
                user_message="Failed to render PDF pages as images.",
                code=ErrorCode.INTERNAL,
            )

        return ConversionResult(
            output_path=primary,
            source_path=source,
            target_format=target,
            extra_outputs=extra,
            message=f"Rendered PDF to {target.upper()}"
            + (f" ({len(extra) + 1} pages)" if extra else ""),
        )

    def _pdf_to_txt(self, source: Path, output_path: Path) -> ConversionResult:
        doc = self._open_pdf(source)
        try:
            parts: list[str] = []
            for page in doc:
                parts.append(page.get_text("text"))
            text = "\n".join(parts)
            output_path.write_text(text, encoding="utf-8")
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                user_message="Failed to extract text from PDF.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc
        finally:
            doc.close()

        return ConversionResult(
            output_path=output_path,
            source_path=source,
            target_format="txt",
            message="Extracted text from PDF",
        )

    def _txt_to_pdf(self, source: Path, output_path: Path) -> ConversionResult:
        try:
            import fitz
        except ImportError as exc:
            raise ConversionError(
                user_message="PyMuPDF is required for TXT→PDF conversion.",
                technical_detail=str(exc),
                code=ErrorCode.MISSING_DEPENDENCY,
            ) from exc

        try:
            text = source.read_text(encoding="utf-8", errors="replace")
            doc = fitz.open()
            # Simple paginated plain-text PDF
            margin = 50
            fontsize = 11
            line_height = fontsize * 1.4
            page_width, page_height = 595, 842  # A4
            usable_width = page_width - 2 * margin
            y_limit = page_height - margin

            def new_page():
                page = doc.new_page(width=page_width, height=page_height)
                return page, margin

            page, y = new_page()
            # crude wrap by character width estimate
            avg_char = fontsize * 0.5
            max_chars = max(20, int(usable_width / avg_char))

            for raw_line in text.splitlines() or [""]:
                while raw_line is not None:
                    chunk = raw_line[:max_chars]
                    rest = raw_line[max_chars:] if len(raw_line) > max_chars else None
                    if y + line_height > y_limit:
                        page, y = new_page()
                    page.insert_text(
                        (margin, y + fontsize),
                        chunk if chunk else " ",
                        fontsize=fontsize,
                        fontname="helv",
                    )
                    y += line_height
                    raw_line = rest

            doc.save(output_path)
            doc.close()
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                user_message="Failed to create PDF from text.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc

        return ConversionResult(
            output_path=output_path,
            source_path=source,
            target_format="pdf",
            message="Created PDF from text",
        )
