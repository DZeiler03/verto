"""FileForge scene frame — ambient smithy backdrop hosting the forge floor."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ui.fileforge.theme import ScenePalette, ThemeMode, palette_for


class ForgeSceneWidget(QWidget):
    """Atmospheric backdrop + horizontal host for oven / anvil / controls / output.

    Children are laid out normally; this widget only paints wall, floor, and a
    soft warm radial light so the smithy feels like one scene.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("forgeScene")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._palette: ScenePalette = palette_for(ThemeMode.FORGE)
        self._glow_x = 0.18  # oven side
        self._forging = False

        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(12, 14, 12, 14)
        self.row.setSpacing(14)

    def set_theme(self, mode: ThemeMode | str) -> None:
        self._palette = palette_for(mode)
        self.update()

    def set_forging(self, forging: bool) -> None:
        self._forging = forging
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        # Wall (top 55%)
        wall = QLinearGradient(0, 0, 0, h * 0.55)
        wall.setColorAt(0.0, QColor(p.wall))
        wall.setColorAt(1.0, QColor(p.bg_mid))
        painter.fillRect(QRectF(0, 0, w, h * 0.55), wall)

        # Floor (bottom)
        floor = QLinearGradient(0, h * 0.5, 0, h)
        floor.setColorAt(0.0, QColor(p.bg_mid))
        floor.setColorAt(0.35, QColor(p.floor))
        floor.setColorAt(1.0, QColor(p.floor))
        painter.fillRect(QRectF(0, h * 0.5, w, h * 0.5), floor)

        # Horizon line (workbench shadow)
        painter.setPen(QColor(p.metal_edge))
        painter.drawLine(int(w * 0.04), int(h * 0.58), int(w * 0.96), int(h * 0.58))

        # Warm light from oven (left)
        gx = w * self._glow_x
        gy = h * 0.48
        radius = max(w, h) * (0.55 if self._forging else 0.42)
        rad = QRadialGradient(gx, gy, radius)
        c0 = QColor(p.glow)
        c0.setAlpha(70 if self._forging else 35)
        c1 = QColor(p.glow)
        c1.setAlpha(0)
        rad.setColorAt(0.0, c0)
        rad.setColorAt(1.0, c1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(rad)
        painter.drawEllipse(QRectF(gx - radius, gy - radius * 0.85, radius * 2, radius * 1.7))

        # Soft vignette
        vig = QRadialGradient(w * 0.5, h * 0.45, max(w, h) * 0.75)
        v0 = QColor(0, 0, 0, 0)
        v1 = QColor(0, 0, 0, 50)
        vig.setColorAt(0.55, v0)
        vig.setColorAt(1.0, v1)
        painter.setBrush(vig)
        painter.drawRect(QRectF(0, 0, w, h))

        painter.end()
