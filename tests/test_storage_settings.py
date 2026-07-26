"""Phase 2 tests: storage staging, download promote, settings persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.settings import AppSettings, load_settings, save_settings
from core.storage import SaveDestination, StorageManager
from core.conversion_queue import ConversionQueue, JobStatus
from morphix.engine import MorphixEngine


def test_staging_and_promote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core import storage as storage_mod

    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(storage_mod, "staging_dir", lambda: staging)

    sm = StorageManager(destination=SaveDestination.DOWNLOADS)
    staged = sm.make_staging_path("png", stem="photo")
    assert staged.parent == staging
    staged.write_bytes(b"fake-png-bytes")

    dest_dir = tmp_path / "Downloads"
    dest_dir.mkdir()
    monkeypatch.setattr(storage_mod, "downloads_dir", lambda: dest_dir)

    final = sm.resolve_save_path(Path("/tmp/photo.png"), "png")
    assert final.parent == dest_dir
    saved = sm.promote(staged, final)
    assert saved.is_file()
    assert saved.read_bytes() == b"fake-png-bytes"
    # staged still exists by default
    assert staged.is_file()


def test_promote_remove_staged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core import storage as storage_mod

    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(storage_mod, "staging_dir", lambda: staging)
    sm = StorageManager()
    staged = sm.make_staging_path("txt", stem="a")
    staged.write_text("hi", encoding="utf-8")
    dest = tmp_path / "out.txt"
    sm.promote(staged, dest, remove_staged=True)
    assert dest.is_file()
    assert not staged.exists()


def test_next_to_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core import storage as storage_mod

    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(storage_mod, "staging_dir", lambda: staging)
    src = tmp_path / "docs" / "report.pdf"
    src.parent.mkdir()
    src.write_bytes(b"%PDF")
    sm = StorageManager(destination=SaveDestination.NEXT_TO_SOURCE)
    path = sm.resolve_save_path(src, "txt")
    assert path.parent == src.parent
    assert path.suffix == ".txt"


def test_stale_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time
    from core import storage as storage_mod

    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(storage_mod, "staging_dir", lambda: staging)
    old = staging / "old.bin"
    old.write_bytes(b"x")
    # Backdate mtime
    old_mtime = time.time() - (25 * 60 * 60)
    import os

    os.utime(old, (old_mtime, old_mtime))
    fresh = staging / "fresh.bin"
    fresh.write_bytes(b"y")

    sm = StorageManager()
    removed = sm.cleanup_stale_on_startup()
    assert removed >= 1
    assert not old.exists()
    assert fresh.exists()


def test_settings_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core import settings as settings_mod

    monkeypatch.setattr(settings_mod, "settings_path", lambda: tmp_path / "settings.json")
    s = AppSettings(
        save_destination=SaveDestination.CUSTOM.value,
        custom_save_dir=str(tmp_path / "out"),
        theme="daylight",
    )
    save_settings(s)
    loaded = load_settings()
    assert loaded.save_destination == "custom"
    assert loaded.theme == "daylight"
    assert loaded.custom_save_dir == str(tmp_path / "out")


def test_queue_stays_staged_until_download(
    fixtures_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core import storage as storage_mod

    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(storage_mod, "staging_dir", lambda: staging)

    engine = MorphixEngine()
    q = ConversionQueue(engine)
    staged = staging / "out.jpg"
    job = q.add(fixtures_dir / "sample.png", "jpg", staged)
    q.process_all_sync()
    job = q.get_job(job.id)
    assert job is not None
    assert job.status == JobStatus.DONE
    assert job.result is not None
    assert job.result.output_path.is_file()
    # Still in staging area
    assert str(staging) in str(job.result.output_path.resolve())

    dest = tmp_path / "Downloads" / "sample.jpg"
    dest.parent.mkdir()
    sm = StorageManager()
    saved = sm.promote(job.result.output_path, dest)
    q.mark_downloaded(job.id, saved)
    job = q.get_job(job.id)
    assert job.status == JobStatus.DOWNLOADED


def test_cancel_pending(fixtures_dir: Path, tmp_path: Path) -> None:
    q = ConversionQueue(MorphixEngine())
    q.add(fixtures_dir / "sample.png", "jpg", tmp_path / "a.jpg")
    q.add(fixtures_dir / "sample.png", "png", tmp_path / "b.png")
    # Cancel before processing
    n = q.cancel_pending()
    assert n == 2
    assert all(j.status == JobStatus.CANCELLED for j in q.jobs)
