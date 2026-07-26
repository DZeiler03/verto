"""Shared fixtures for Verto / Morphix tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    """Create small sample files for conversion tests."""
    root = tmp_path / "fixtures"
    root.mkdir()

    # 1x1 PNG via Pillow
    from PIL import Image

    png = root / "sample.png"
    Image.new("RGB", (8, 8), color=(200, 40, 40)).save(png)

    jpg = root / "sample.jpg"
    Image.new("RGB", (8, 8), color=(40, 40, 200)).save(jpg, quality=90)

    # Minimal PDF via PyMuPDF
    import fitz

    pdf = root / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((20, 40), "Hello Verto Morphix", fontsize=12)
    doc.save(pdf)
    doc.close()

    # Empty file
    empty = root / "empty.png"
    empty.write_bytes(b"")

    # Corrupt "png"
    corrupt = root / "corrupt.png"
    corrupt.write_bytes(b"not-a-real-png-file")

    # Google pointer
    gdoc = root / "notes.gdoc"
    gdoc.write_text(
        json.dumps(
            {
                "url": "https://docs.google.com/document/d/abc123/edit",
                "doc_id": "abc123",
            }
        ),
        encoding="utf-8",
    )

    # CSV
    csv_path = root / "sample.csv"
    csv_path.write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")

    # XLSX
    from openpyxl import Workbook

    xlsx = root / "sample.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["name", "value"])
    ws.append(["alpha", 1])
    ws.append(["beta", 2])
    wb.save(xlsx)

    # TXT
    txt = root / "sample.txt"
    txt.write_text("Forged by Morphix.\nLine two.\n", encoding="utf-8")

    return root


@pytest.fixture
def engine():
    from morphix.engine import MorphixEngine

    return MorphixEngine()
