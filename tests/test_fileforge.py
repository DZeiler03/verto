"""Smoke tests for FileForge theme modules (no display server required for imports)."""

from __future__ import annotations


def test_stylesheet_forge() -> None:
    from ui.fileforge.theme import ThemeMode, stylesheet

    qss = stylesheet(ThemeMode.FORGE)
    assert "QMainWindow" in qss
    assert "#E85D04" in qss or "E85D04" in qss


def test_stylesheet_daylight() -> None:
    from ui.fileforge.theme import ThemeMode, stylesheet

    qss = stylesheet(ThemeMode.DAYLIGHT)
    assert "QMainWindow" in qss
    assert "F5F0E8" in qss or "f5f0e8" in qss.lower()


def test_fileforge_exports() -> None:
    from ui.fileforge import (
        AnvilWidget,
        ForgeQueueRow,
        HammerOverlay,
        OutputSlot,
        ThemeMode,
        stylesheet,
    )

    assert callable(stylesheet)
    assert ThemeMode.FORGE.value == "forge"
    assert AnvilWidget is not None
    assert HammerOverlay is not None
    assert OutputSlot is not None
    assert ForgeQueueRow is not None
