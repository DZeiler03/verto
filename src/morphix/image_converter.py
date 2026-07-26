"""Morphix image converter — Pillow + img2pdf (offline)."""

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

logger = logging.getLogger("verto.morphix.image")

# Formats Morphix handles via Pillow / img2pdf
_RASTER = {"jpg", "jpeg", "png", "bmp", "webp", "tiff", "tif", "gif"}
_PIL_SAVE = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "bmp": "BMP",
    "webp": "WEBP",
    "tiff": "TIFF",
    "tif": "TIFF",
    "gif": "GIF",
}


class ImageConverter(BaseConverter):
    """Convert between common raster formats and images → PDF."""

    name = "image"

    input_formats = {"jpg", "png", "bmp", "webp", "tiff", "gif"}
    output_formats = {"jpg", "png", "bmp", "webp", "tiff", "gif", "pdf"}

    def can_convert(self, source_format: str, target_format: str) -> bool:
        src = normalize_format(source_format)
        if src == "jpeg":
            src = "jpg"
        if src == "tif":
            src = "tiff"
        dst = normalize_format(target_format)
        if dst == "jpeg":
            dst = "jpg"
        if dst == "tif":
            dst = "tiff"
        return super().can_convert(src, dst)

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
        if target == "tif":
            target = "tiff"

        if not source.is_file():
            raise ConversionError(
                user_message="Source image not found.",
                technical_detail=str(source),
                code=ErrorCode.IO_ERROR,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if target == "pdf":
            return self._to_pdf(source, output_path, options)

        return self._raster_convert(source, target, output_path, options)

    def _raster_convert(
        self,
        source: Path,
        target: str,
        output_path: Path,
        options: dict[str, Any],
    ) -> ConversionResult:
        try:
            from PIL import Image
        except ImportError as exc:
            raise ConversionError(
                user_message="Pillow is required for image conversion.",
                technical_detail=str(exc),
                code=ErrorCode.MISSING_DEPENDENCY,
            ) from exc

        try:
            with Image.open(source) as img:
                # Handle multi-frame (GIF/TIFF): convert first frame for most targets
                # unless both support multi-frame
                frames: list[Any] = []
                try:
                    while True:
                        frames.append(img.copy())
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                if not frames:
                    frames = [img.copy()]

                primary = frames[0]
                pil_format = _PIL_SAVE.get(target, target.upper())

                # JPEG/WebP/BMP don't support alpha — flatten
                if target in {"jpg", "bmp"} and primary.mode in {"RGBA", "LA", "P"}:
                    background = Image.new("RGB", primary.size, (255, 255, 255))
                    if primary.mode == "P":
                        primary = primary.convert("RGBA")
                    if primary.mode in {"RGBA", "LA"}:
                        alpha = primary.split()[-1]
                        background.paste(primary.convert("RGB"), mask=alpha)
                        primary = background
                    else:
                        primary = primary.convert("RGB")
                elif target == "jpg" and primary.mode != "RGB":
                    primary = primary.convert("RGB")

                save_kwargs: dict[str, Any] = {}
                if target == "jpg":
                    save_kwargs["quality"] = int(options.get("quality", 92))
                    save_kwargs["optimize"] = True
                if target == "webp":
                    save_kwargs["quality"] = int(options.get("quality", 90))

                if target in {"gif", "tiff"} and len(frames) > 1:
                    # Attempt multi-frame save
                    converted_frames = []
                    for fr in frames:
                        if target == "gif" and fr.mode not in {"P", "L"}:
                            fr = fr.convert("P", palette=Image.Palette.ADAPTIVE)
                        converted_frames.append(fr)
                    converted_frames[0].save(
                        output_path,
                        format=pil_format,
                        save_all=True,
                        append_images=converted_frames[1:],
                        **save_kwargs,
                    )
                else:
                    primary.save(output_path, format=pil_format, **save_kwargs)

        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Image conversion failed")
            raise ConversionError(
                user_message="Could not convert this image. It may be corrupted or unsupported.",
                technical_detail=str(exc),
                code=ErrorCode.CORRUPT,
            ) from exc

        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise ConversionError(
                user_message="Image conversion produced an empty file.",
                code=ErrorCode.IO_ERROR,
            )

        return ConversionResult(
            output_path=output_path,
            source_path=source,
            target_format=target,
            message=f"Converted image to {target.upper()}",
        )

    def _to_pdf(
        self,
        source: Path,
        output_path: Path,
        options: dict[str, Any],
    ) -> ConversionResult:
        extra_images: list[Path] = list(options.get("extra_images") or [])
        sources = [source, *extra_images]

        try:
            import img2pdf
        except ImportError:
            return self._to_pdf_via_pillow(sources, source, output_path)

        try:
            # img2pdf wants raw bytes paths; convert non-JPEG/PNG if needed via temp
            from PIL import Image
            import tempfile
            import io

            pdf_inputs: list[bytes] = []
            tmp_files: list[Path] = []
            try:
                for img_path in sources:
                    lower = img_path.suffix.lower()
                    if lower in {".jpg", ".jpeg", ".png"}:
                        pdf_inputs.append(Path(img_path).read_bytes())
                    else:
                        with Image.open(img_path) as im:
                            if im.mode in {"RGBA", "LA", "P"}:
                                background = Image.new("RGB", im.size, (255, 255, 255))
                                if im.mode == "P":
                                    im = im.convert("RGBA")
                                if im.mode in {"RGBA", "LA"}:
                                    background.paste(im.convert("RGB"), mask=im.split()[-1])
                                    im = background
                                else:
                                    im = im.convert("RGB")
                            elif im.mode != "RGB":
                                im = im.convert("RGB")
                            buf = io.BytesIO()
                            im.save(buf, format="JPEG", quality=92)
                            pdf_inputs.append(buf.getvalue())

                data = img2pdf.convert(*pdf_inputs)
                output_path.write_bytes(data)
            finally:
                for t in tmp_files:
                    try:
                        t.unlink(missing_ok=True)
                    except OSError:
                        pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("img2pdf failed, falling back to Pillow: %s", exc)
            return self._to_pdf_via_pillow(sources, source, output_path)

        return ConversionResult(
            output_path=output_path,
            source_path=source,
            target_format="pdf",
            message="Converted image(s) to PDF",
        )

    def _to_pdf_via_pillow(
        self,
        sources: list[Path],
        primary_source: Path,
        output_path: Path,
    ) -> ConversionResult:
        try:
            from PIL import Image
        except ImportError as exc:
            raise ConversionError(
                user_message="Pillow is required for image→PDF conversion.",
                technical_detail=str(exc),
                code=ErrorCode.MISSING_DEPENDENCY,
            ) from exc

        try:
            images = []
            for p in sources:
                im = Image.open(p)
                if im.mode != "RGB":
                    im = im.convert("RGB")
                images.append(im)
            first, rest = images[0], images[1:]
            first.save(output_path, "PDF", save_all=True, append_images=rest)
            for im in images:
                im.close()
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(
                user_message="Could not convert image(s) to PDF.",
                technical_detail=str(exc),
                code=ErrorCode.CORRUPT,
            ) from exc

        return ConversionResult(
            output_path=output_path,
            source_path=primary_source,
            target_format="pdf",
            message="Converted image(s) to PDF",
        )
