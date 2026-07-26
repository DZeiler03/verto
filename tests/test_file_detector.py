"""Tests for core.file_detector."""

from __future__ import annotations

from pathlib import Path

from core.file_detector import FileCategory, FileDetector
from morphix.base import GOOGLE_POINTER_MESSAGE, ConversionError, ErrorCode


def test_detect_png(fixtures_dir: Path) -> None:
    det = FileDetector()
    info = det.detect(fixtures_dir / "sample.png")
    assert info.category == FileCategory.IMAGE
    assert info.format == "png"
    assert info.readable is True


def test_detect_pdf(fixtures_dir: Path) -> None:
    det = FileDetector()
    info = det.detect(fixtures_dir / "sample.pdf")
    assert info.category == FileCategory.PDF
    assert info.readable is True


def test_detect_google_pointer(fixtures_dir: Path) -> None:
    det = FileDetector()
    info = det.detect(fixtures_dir / "notes.gdoc")
    assert info.is_google_pointer is True
    assert info.category == FileCategory.GOOGLE_LINK
    assert GOOGLE_POINTER_MESSAGE in info.detail


def test_ensure_convertible_rejects_google(fixtures_dir: Path) -> None:
    det = FileDetector()
    try:
        det.ensure_convertible(fixtures_dir / "notes.gdoc")
        assert False, "expected ConversionError"
    except ConversionError as exc:
        assert exc.code == ErrorCode.GOOGLE_POINTER
        assert "Google Drive" in exc.user_message


def test_empty_file(fixtures_dir: Path) -> None:
    det = FileDetector()
    info = det.detect(fixtures_dir / "empty.png")
    assert info.readable is False


def test_corrupt_image(fixtures_dir: Path) -> None:
    det = FileDetector()
    info = det.detect(fixtures_dir / "corrupt.png")
    assert info.readable is False
