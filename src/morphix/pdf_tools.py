"""Morphix PDF tools — merge, split, and compress (PyMuPDF, offline)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from morphix.base import ConversionError, ConversionResult, ErrorCode

logger = logging.getLogger("verto.morphix.pdf_tools")


def _open_fitz():
    try:
        import fitz
    except ImportError as exc:
        raise ConversionError(
            user_message="PyMuPDF is required for PDF tools.",
            technical_detail=str(exc),
            code=ErrorCode.MISSING_DEPENDENCY,
        ) from exc
    return fitz


class PdfTools:
    """Local PDF merge / split / compress used by Morphix and the Tools UI."""

    def merge(
        self,
        sources: list[Path],
        output_path: Path,
    ) -> ConversionResult:
        fitz = _open_fitz()
        if len(sources) < 2:
            raise ConversionError(
                user_message="Merge needs at least two PDF files.",
                code=ErrorCode.UNSUPPORTED,
            )
        for p in sources:
            if not Path(p).is_file():
                raise ConversionError(
                    user_message=f"Missing PDF: {p}",
                    code=ErrorCode.IO_ERROR,
                )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        primary = Path(sources[0])

        try:
            merged = fitz.open()
            try:
                for src in sources:
                    doc = fitz.open(src)
                    try:
                        if doc.is_encrypted and not doc.authenticate(""):
                            raise ConversionError(
                                user_message=f"Password-protected PDF cannot be merged: {Path(src).name}",
                                code=ErrorCode.CORRUPT,
                            )
                        merged.insert_pdf(doc)
                    finally:
                        doc.close()
                merged.save(output_path, garbage=4, deflate=True)
            finally:
                merged.close()
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                user_message="Failed to merge PDFs.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc

        return ConversionResult(
            output_path=output_path,
            source_path=primary,
            target_format="pdf",
            message=f"Merged {len(sources)} PDFs",
        )

    def split(
        self,
        source: Path,
        output_dir: Path,
        *,
        stem: str | None = None,
    ) -> ConversionResult:
        fitz = _open_fitz()
        source = Path(source)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        name = stem or source.stem

        try:
            doc = fitz.open(source)
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
                extras: list[Path] = []
                primary: Path | None = None
                for i in range(doc.page_count):
                    out = output_dir / f"{name}_page{i + 1}.pdf"
                    single = fitz.open()
                    try:
                        single.insert_pdf(doc, from_page=i, to_page=i)
                        single.save(out, garbage=3, deflate=True)
                    finally:
                        single.close()
                    if i == 0:
                        primary = out
                    else:
                        extras.append(out)
            finally:
                doc.close()
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                user_message="Failed to split PDF.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc

        assert primary is not None
        return ConversionResult(
            output_path=primary,
            source_path=source,
            target_format="pdf",
            extra_outputs=extras,
            message=f"Split into {1 + len(extras)} page PDF(s)",
        )

    def compress(
        self,
        source: Path,
        output_path: Path,
        options: dict[str, Any] | None = None,
    ) -> ConversionResult:
        """Compress a PDF by re-saving with garbage collection, deflate, and image downsampling."""
        fitz = _open_fitz()
        options = options or {}
        source = Path(source)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Image DPI target for recompress (lower = smaller)
        dpi = int(options.get("dpi", 100))
        jpeg_quality = int(options.get("quality", 70))

        try:
            doc = fitz.open(source)
            try:
                if doc.is_encrypted and not doc.authenticate(""):
                    raise ConversionError(
                        user_message="This PDF is password-protected.",
                        code=ErrorCode.CORRUPT,
                    )

                # Rebuild pages with optionally downscaled rendered images for heavy scans
                # Prefer structure-preserving save first; then optional image rewrite
                rewrite_images = bool(options.get("rewrite_images", True))
                if rewrite_images and doc.page_count > 0:
                    out_doc = fitz.open()
                    try:
                        zoom = dpi / 72.0
                        matrix = fitz.Matrix(zoom, zoom)
                        for page in doc:
                            pix = page.get_pixmap(matrix=matrix, alpha=False)
                            # Insert as JPEG-compressed image page
                            img_pdf = fitz.open()
                            try:
                                rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                                img_page = img_pdf.new_page(width=rect.width, height=rect.height)
                                # Save pixmap to JPEG bytes
                                img_bytes = pix.tobytes("jpeg", jpg_quality=jpeg_quality)
                                img_page.insert_image(rect, stream=img_bytes)
                                out_doc.insert_pdf(img_pdf)
                            finally:
                                img_pdf.close()
                        # If rewrite produced something larger, fall back to deflate-only
                        tmp = output_path.with_suffix(".tmp.pdf")
                        out_doc.save(
                            tmp,
                            garbage=4,
                            deflate=True,
                            clean=True,
                        )
                        orig_size = source.stat().st_size
                        new_size = tmp.stat().st_size
                        if new_size < orig_size or options.get("force_rewrite"):
                            tmp.replace(output_path)
                        else:
                            # Structure-preserving compress
                            tmp.unlink(missing_ok=True)
                            doc.save(
                                output_path,
                                garbage=4,
                                deflate=True,
                                clean=True,
                            )
                    finally:
                        out_doc.close()
                else:
                    doc.save(
                        output_path,
                        garbage=4,
                        deflate=True,
                        clean=True,
                    )
            finally:
                doc.close()
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("PDF compress failed")
            raise ConversionError(
                user_message="Failed to compress PDF.",
                technical_detail=str(exc),
                code=ErrorCode.INTERNAL,
            ) from exc

        if not output_path.is_file():
            raise ConversionError(
                user_message="Compress produced no output.",
                code=ErrorCode.IO_ERROR,
            )

        before = source.stat().st_size
        after = output_path.stat().st_size
        pct = (1 - after / before) * 100 if before else 0
        return ConversionResult(
            output_path=output_path,
            source_path=source,
            target_format="pdf",
            message=f"Compressed PDF ({before // 1024} KiB → {after // 1024} KiB, {pct:.0f}% smaller)"
            if after < before
            else f"Re-saved PDF ({after // 1024} KiB; already compact)",
        )
