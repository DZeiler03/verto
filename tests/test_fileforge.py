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


def test_palette_differs_by_theme() -> None:
    from ui.fileforge.theme import ThemeMode, palette_for

    forge = palette_for(ThemeMode.FORGE)
    day = palette_for(ThemeMode.DAYLIGHT)
    assert forge.bg != day.bg
    assert forge.glow
    assert day.flame_core


def test_fileforge_exports() -> None:
    from ui.fileforge import (
        AnvilWidget,
        ForgeOvenWidget,
        ForgeQueueRow,
        ForgeSceneWidget,
        HammerOverlay,
        OutputSlot,
        ThemeMode,
        palette_for,
        stylesheet,
    )

    assert callable(stylesheet)
    assert callable(palette_for)
    assert ThemeMode.FORGE.value == "forge"
    assert AnvilWidget is not None
    assert HammerOverlay is not None
    assert OutputSlot is not None
    assert ForgeQueueRow is not None
    assert ForgeOvenWidget is not None
    assert ForgeSceneWidget is not None


def test_oven_and_scene_theme_offscreen() -> None:
    """Instantiate scene widgets under offscreen Qt (no crash)."""
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    from ui.fileforge import (
        AnvilWidget,
        ForgeOvenWidget,
        ForgeSceneWidget,
        OutputSlot,
        ThemeMode,
    )

    oven = ForgeOvenWidget()
    oven.set_theme(ThemeMode.FORGE)
    oven.set_forging(True)
    oven.set_forging(False)
    oven.set_theme(ThemeMode.DAYLIGHT)

    scene = ForgeSceneWidget()
    scene.set_theme(ThemeMode.DAYLIGHT)
    scene.set_forging(True)

    anvil = AnvilWidget()
    anvil.set_theme(ThemeMode.FORGE)
    anvil.set_forging(True)

    out = OutputSlot()
    out.set_theme(ThemeMode.DAYLIGHT)
    out.set_ready("demo.pdf", ext="pdf")

    # Keep refs so GC doesn't destroy mid-test
    assert oven is not None and scene is not None and anvil is not None and out is not None
    assert app is not None
