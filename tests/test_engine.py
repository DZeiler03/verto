"""Tests for MorphixEngine orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from morphix.base import ConversionError, ErrorCode
from morphix.engine import MorphixEngine


def test_list_targets_png(engine: MorphixEngine, fixtures_dir: Path) -> None:
    targets = engine.list_target_formats(fixtures_dir / "sample.png")
    assert "jpg" in targets
    assert "pdf" in targets
    assert "png" not in targets


def test_list_targets_pdf(engine: MorphixEngine, fixtures_dir: Path) -> None:
    targets = engine.list_target_formats(fixtures_dir / "sample.pdf")
    assert "txt" in targets
    assert "png" in targets


def test_convert_png_to_jpg(engine: MorphixEngine, fixtures_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "converted.jpg"
    result = engine.convert(fixtures_dir / "sample.png", "jpg", out)
    assert result.output_path.is_file()


def test_google_pointer_raises(engine: MorphixEngine, fixtures_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(ConversionError) as ei:
        engine.convert(fixtures_dir / "notes.gdoc", "pdf", tmp_path / "x.pdf")
    assert ei.value.code == ErrorCode.GOOGLE_POINTER


def test_unsupported_raises(engine: MorphixEngine, fixtures_dir: Path, tmp_path: Path) -> None:
    with pytest.raises(ConversionError) as ei:
        engine.convert(fixtures_dir / "sample.png", "docx", tmp_path / "x.docx")
    assert ei.value.code == ErrorCode.UNSUPPORTED


def test_queue_sync(fixtures_dir: Path, tmp_path: Path) -> None:
    from core.conversion_queue import ConversionQueue, JobStatus

    q = ConversionQueue(MorphixEngine())
    q.add(fixtures_dir / "sample.png", "jpg", tmp_path / "a.jpg")
    q.add(fixtures_dir / "sample.pdf", "txt", tmp_path / "b.txt")
    jobs = q.process_all_sync()
    assert all(j.status == JobStatus.DONE for j in jobs)


def test_storage_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core import storage as storage_mod
    from core.storage import StorageManager

    monkeypatch.setattr(storage_mod, "staging_dir", lambda: tmp_path / "staging")
    (tmp_path / "staging").mkdir()
    sm = StorageManager()
    path = sm.make_staging_path("png", stem="item")
    assert path.parent == tmp_path / "staging"
    path.write_bytes(b"abc")
    dest = tmp_path / "out" / "item.png"
    saved = sm.promote(path, dest)
    assert saved.is_file()
