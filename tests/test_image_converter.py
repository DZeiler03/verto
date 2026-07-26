"""Tests for Morphix ImageConverter."""

from __future__ import annotations

from pathlib import Path

from morphix.image_converter import ImageConverter


def test_png_to_jpg(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = ImageConverter()
    out = tmp_path / "out.jpg"
    result = conv.convert(fixtures_dir / "sample.png", "jpg", out)
    assert result.output_path.is_file()
    assert result.output_path.stat().st_size > 0


def test_jpg_to_png(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = ImageConverter()
    out = tmp_path / "out.png"
    result = conv.convert(fixtures_dir / "sample.jpg", "png", out)
    assert result.output_path.is_file()


def test_png_to_webp(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = ImageConverter()
    out = tmp_path / "out.webp"
    result = conv.convert(fixtures_dir / "sample.png", "webp", out)
    assert result.output_path.is_file()


def test_png_to_pdf(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = ImageConverter()
    out = tmp_path / "out.pdf"
    result = conv.convert(fixtures_dir / "sample.png", "pdf", out)
    assert result.output_path.is_file()
    assert result.output_path.stat().st_size > 0
