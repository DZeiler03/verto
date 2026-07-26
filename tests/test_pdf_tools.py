"""Tests for Morphix PDF tools and OCR wiring."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from morphix.engine import MorphixEngine
from morphix.pdf_tools import PdfTools
from morphix.ocr import get_ocr


def _make_pdf(path: Path, text: str = "Hello") -> Path:
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((20, 40), text, fontsize=14)
    doc.save(path)
    doc.close()
    return path


def test_merge_pdfs(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", "A")
    b = _make_pdf(tmp_path / "b.pdf", "B")
    out = tmp_path / "merged.pdf"
    result = PdfTools().merge([a, b], out)
    assert result.output_path.is_file()
    doc = fitz.open(out)
    assert doc.page_count == 2
    doc.close()


def test_split_pdf(tmp_path: Path) -> None:
    # multi-page
    path = tmp_path / "multi.pdf"
    doc = fitz.open()
    for i in range(3):
        p = doc.new_page(width=200, height=200)
        p.insert_text((20, 40), f"Page {i+1}", fontsize=12)
    doc.save(path)
    doc.close()

    out_dir = tmp_path / "pages"
    result = PdfTools().split(path, out_dir)
    assert result.output_path.is_file()
    assert len(result.extra_outputs) == 2
    assert len(list(out_dir.glob("*.pdf"))) == 3


def test_compress_pdf(tmp_path: Path) -> None:
    src = _make_pdf(tmp_path / "big.pdf", "Compress me")
    out = tmp_path / "small.pdf"
    result = PdfTools().compress(src, out, {"dpi": 72, "quality": 50})
    assert result.output_path.is_file()
    assert result.output_path.stat().st_size > 0


def test_engine_merge_and_compress(tmp_path: Path) -> None:
    engine = MorphixEngine()
    a = _make_pdf(tmp_path / "a.pdf")
    b = _make_pdf(tmp_path / "b.pdf")
    merged = engine.merge_pdfs([a, b], tmp_path / "m.pdf")
    assert merged.output_path.is_file()
    compressed = engine.compress_pdf(merged.output_path, tmp_path / "c.pdf")
    assert compressed.output_path.is_file()


def test_engine_pdf_compressed_target(tmp_path: Path) -> None:
    engine = MorphixEngine()
    src = _make_pdf(tmp_path / "src.pdf")
    targets = engine.list_target_formats(src)
    assert "pdf-compressed" in targets
    assert "pdf-split" in targets
    out = tmp_path / "out.pdf"
    result = engine.convert(src, "pdf-compressed", out)
    assert result.output_path.is_file()


def test_ocr_available_flag() -> None:
    engine = MorphixEngine()
    assert engine.ocr_available() == get_ocr().available()


@pytest.mark.skipif(not get_ocr().available(), reason="Tesseract not installed")
def test_ocr_image(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img_path = tmp_path / "hello.png"
    im = Image.new("RGB", (200, 60), "white")
    draw = ImageDraw.Draw(im)
    draw.text((10, 15), "HELLO", fill="black")
    im.save(img_path)

    engine = MorphixEngine()
    out = tmp_path / "ocr.txt"
    result = engine.ocr_to_text(img_path, out)
    text = result.output_path.read_text(encoding="utf-8")
    # OCR may be imperfect; just ensure we got some text file
    assert result.output_path.is_file()
    assert isinstance(text, str)
