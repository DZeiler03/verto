"""FileForge forge oven — stylized 2D smithy furnace with light flame/ember motion.

Animation is intentionally cheap: a single QTimer advances a phase float; fixed
lists of flame and ember params are mutated in place (no per-frame alloc).
Timer pauses when the widget is hidden.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from ui.fileforge.theme import ScenePalette, ThemeMode, palette_for


@dataclass
class _Ember:
    """Pre-allocated ember particle (mutated each tick)."""

    x: float  # 0..1 relative to mouth
    y: float  # 0..1, 0 = mouth bottom, rises upward
    speed: float
    size: float
    phase: float
    life: float  # 0..1


class ForgeOvenWidget(QWidget):
    """Decorative blacksmith oven with subtle flame + ember animation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(120, 180)
        self.setMaximumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self._palette: ScenePalette = palette_for(ThemeMode.FORGE)
        self._forging = False
        self._phase = 0.0  # continuous time for sin waves
        self._rng = random.Random(42)

        # Fixed flame anchor offsets (relative 0..1 across mouth width)
        self._flame_offsets = [0.15, 0.30, 0.45, 0.55, 0.70, 0.85]
        self._embers: list[_Ember] = [
            _Ember(
                x=self._rng.uniform(0.15, 0.85),
                y=self._rng.uniform(0.0, 1.0),
                speed=self._rng.uniform(0.008, 0.02),
                size=self._rng.uniform(1.5, 3.5),
                phase=self._rng.uniform(0, math.tau),
                life=self._rng.uniform(0.3, 1.0),
            )
            for _ in range(10)
        ]

        # ~22 FPS is enough for soft fire; keeps CPU light
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_theme(self, mode: ThemeMode | str) -> None:
        self._palette = palette_for(mode)
        self.update()

    def set_forging(self, forging: bool) -> None:
        """Brighten fire while Morphix is converting."""
        self._forging = forging
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        # Advance phase; slightly faster when forging
        step = 0.07 if self._forging else 0.045
        self._phase = (self._phase + step) % (math.tau * 4)

        boost = 1.6 if self._forging else 1.0
        for e in self._embers:
            e.y -= e.speed * boost
            e.x += math.sin(self._phase + e.phase) * 0.004
            e.life -= 0.012 * boost
            if e.y < -0.15 or e.life <= 0:
                # Respawn at mouth
                e.x = self._rng.uniform(0.2, 0.8)
                e.y = self._rng.uniform(0.85, 1.05)
                e.speed = self._rng.uniform(0.008, 0.022)
                e.size = self._rng.uniform(1.5, 3.5)
                e.phase = self._rng.uniform(0, math.tau)
                e.life = self._rng.uniform(0.5, 1.0)

        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        # Layout: body sits in lower ~75%, chimney on top
        body = QRectF(w * 0.08, h * 0.18, w * 0.84, h * 0.72)
        mouth = QRectF(
            body.left() + body.width() * 0.18,
            body.top() + body.height() * 0.28,
            body.width() * 0.64,
            body.height() * 0.42,
        )
        chimney = QRectF(
            body.left() + body.width() * 0.32,
            h * 0.02,
            body.width() * 0.36,
            body.top() - h * 0.02 + 4,
        )

        # Soft ambient glow behind oven (warmer when forging)
        glow_r = max(body.width(), body.height()) * (0.85 if self._forging else 0.7)
        rad = QRadialGradient(mouth.center(), glow_r)
        gc = QColor(p.glow)
        gc.setAlpha(90 if self._forging else 45)
        rad.setColorAt(0.0, gc)
        transparent = QColor(p.glow)
        transparent.setAlpha(0)
        rad.setColorAt(1.0, transparent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(rad)
        painter.drawEllipse(mouth.center(), glow_r, glow_r * 0.9)

        # Chimney
        self._draw_stone_block(painter, chimney, p)
        # Body
        self._draw_stone_block(painter, body, p)

        # Iron frame around mouth
        frame = mouth.adjusted(-4, -4, 4, 4)
        painter.setPen(QPen(QColor(p.metal_edge), 2))
        grad = QLinearGradient(frame.topLeft(), frame.bottomRight())
        grad.setColorAt(0.0, QColor(p.metal_mid))
        grad.setColorAt(0.5, QColor(p.metal_dark))
        grad.setColorAt(1.0, QColor(p.metal_light))
        painter.setBrush(grad)
        painter.drawRoundedRect(frame, 4, 4)

        # Dark cavity
        cavity = QRadialGradient(mouth.center().x(), mouth.bottom(), mouth.height())
        cavity.setColorAt(0.0, QColor(p.flame_edge))
        cavity.setColorAt(0.35, QColor("#1A0800"))
        cavity.setColorAt(1.0, QColor("#050302"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(cavity)
        painter.drawRoundedRect(mouth, 3, 3)

        # Grate lines
        painter.setPen(QPen(QColor(p.metal_mid), 1))
        for i in range(1, 4):
            y = mouth.top() + mouth.height() * (i / 4.0)
            painter.drawLine(
                int(mouth.left() + 4),
                int(y),
                int(mouth.right() - 4),
                int(y),
            )

        # Flames (simple teardrop polygons with sin height)
        intensity = 1.25 if self._forging else 1.0
        for i, ox in enumerate(self._flame_offsets):
            # Phase offset per flame for desync
            wave = math.sin(self._phase * (1.2 + i * 0.08) + i * 1.1)
            height_factor = (0.55 + 0.35 * wave) * intensity
            base_x = mouth.left() + mouth.width() * ox
            base_y = mouth.bottom() - 4
            tip_y = base_y - mouth.height() * height_factor
            half_w = mouth.width() * (0.07 + 0.02 * math.sin(self._phase + i))

            path = QPainterPath()
            path.moveTo(base_x - half_w, base_y)
            path.quadTo(base_x - half_w * 0.3, (base_y + tip_y) * 0.5, base_x, tip_y)
            path.quadTo(base_x + half_w * 0.3, (base_y + tip_y) * 0.5, base_x + half_w, base_y)
            path.closeSubpath()

            # Outer flame
            outer = QColor(p.flame_edge)
            outer.setAlpha(int(160 + 40 * wave))
            painter.setBrush(outer)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)

            # Inner core (smaller)
            core = QPainterPath()
            core.moveTo(base_x - half_w * 0.4, base_y - 2)
            core.quadTo(base_x, tip_y + mouth.height() * 0.12, base_x + half_w * 0.4, base_y - 2)
            core.closeSubpath()
            inner = QColor(p.flame_core)
            inner.setAlpha(int(180 + 50 * wave))
            painter.setBrush(inner)
            painter.drawPath(core)

        # Embers rising from mouth
        for e in self._embers:
            if e.life <= 0:
                continue
            ex = mouth.left() + mouth.width() * e.x
            ey = mouth.top() + mouth.height() * e.y
            alpha = max(0, min(255, int(220 * e.life * (1.1 if self._forging else 0.85))))
            col = QColor(p.ember if e.size > 2.2 else p.flame_mid)
            col.setAlpha(alpha)
            painter.setBrush(col)
            painter.setPen(Qt.PenStyle.NoPen)
            r = e.size * (1.2 if self._forging else 1.0)
            painter.drawEllipse(QRectF(ex - r, ey - r, r * 2, r * 2))

        # Caption
        painter.setPen(QColor(p.text_dim))
        painter.drawText(
            QRectF(0, body.bottom() + 2, w, 16),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "Forge oven" + (" · hot" if self._forging else ""),
        )
        painter.end()

    def _draw_stone_block(self, painter: QPainter, rect: QRectF, p: ScenePalette) -> None:
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(p.stone))
        grad.setColorAt(0.45, QColor(p.metal_dark))
        grad.setColorAt(1.0, QColor(p.stone))
        painter.setPen(QPen(QColor(p.metal_edge), 1.5))
        painter.setBrush(grad)
        painter.drawRoundedRect(rect, 6, 6)
        # Brick lines (subtle)
        painter.setPen(QPen(QColor(p.metal_edge), 1))
        mid_y = rect.center().y()
        painter.drawLine(int(rect.left() + 6), int(mid_y), int(rect.right() - 6), int(mid_y))
        painter.drawLine(
            int(rect.center().x()),
            int(rect.top() + 6),
            int(rect.center().x()),
            int(rect.bottom() - 6),
        )
