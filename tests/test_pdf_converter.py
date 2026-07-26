"""Tests for Morphix PdfConverter."""

from __future__ import annotations

from pathlib import Path

from morphix.pdf_converter import PdfConverter


def test_pdf_to_txt(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = PdfConverter()
    out = tmp_path / "out.txt"
    result = conv.convert(fixtures_dir / "sample.pdf", "txt", out)
    text = result.output_path.read_text(encoding="utf-8")
    assert "Morphix" in text or "Hello" in text


def test_pdf_to_png(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = PdfConverter()
    out = tmp_path / "page.png"
    result = conv.convert(fixtures_dir / "sample.pdf", "png", out)
    assert result.output_path.is_file()
    assert result.output_path.stat().st_size > 0


def test_pdf_to_jpg(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = PdfConverter()
    out = tmp_path / "page.jpg"
    result = conv.convert(fixtures_dir / "sample.pdf", "jpg", out)
    assert result.output_path.is_file()


def test_txt_to_pdf(fixtures_dir: Path, tmp_path: Path) -> None:
    conv = PdfConverter()
    out = tmp_path / "from_txt.pdf"
    result = conv.convert(fixtures_dir / "sample.txt", "pdf", out)
    assert result.output_path.is_file()
    # reopen with fitz
    import fitz

    doc = fitz.open(result.output_path)
    assert doc.page_count >= 1
    doc.close()
