"""FileForge hammer-strike animation over the anvil."""

from __future__ import annotations

import math

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.fileforge.theme import ScenePalette, ThemeMode, palette_for


class HammerOverlay(QWidget):
    """Animated hammer that loops while forging, then plays a final strike + sparks."""

    strike_finished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._angle = -40.0
        self._spark = 0.0
        self._visible_anim = False
        self._looping = False
        self._palette: ScenePalette = palette_for(ThemeMode.FORGE)

        self._anim = QPropertyAnimation(self, b"angle", self)
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.InQuad)

        self._spark_anim = QPropertyAnimation(self, b"spark", self)
        self._spark_anim.setDuration(350)
        self._spark_anim.setStartValue(1.0)
        self._spark_anim.setEndValue(0.0)

        self._loop_timer = QTimer(self)
        self._loop_timer.setInterval(320)
        self._loop_timer.timeout.connect(self._loop_strike)

        self.hide()

    def set_theme(self, mode: ThemeMode | str) -> None:
        self._palette = palette_for(mode)
        self.update()

    def get_angle(self) -> float:
        return self._angle

    def set_angle(self, value: float) -> None:
        self._angle = value
        self.update()

    angle = Property(float, get_angle, set_angle)

    def get_spark(self) -> float:
        return self._spark

    def set_spark(self, value: float) -> None:
        self._spark = value
        self.update()

    spark = Property(float, get_spark, set_spark)

    def start_loop(self) -> None:
        self._looping = True
        self._visible_anim = True
        self.show()
        self.raise_()
        self._loop_strike()
        self._loop_timer.start()

    def stop_with_finale(self, success: bool = True) -> None:
        self._looping = False
        self._loop_timer.stop()
        self._visible_anim = True
        self.show()
        self.raise_()

        self._anim.stop()
        self._anim.setStartValue(-55.0)
        self._anim.setEndValue(8.0)
        self._anim.setDuration(200)

        def _on_finished() -> None:
            if success:
                self._spark_anim.stop()
                self._spark_anim.start()
            QTimer.singleShot(400, self._hide_after)

        try:
            self._anim.finished.disconnect()
        except RuntimeError:
            pass
        self._anim.finished.connect(_on_finished)
        self._anim.start()

    def stop_immediate(self) -> None:
        self._looping = False
        self._loop_timer.stop()
        self._anim.stop()
        self._spark_anim.stop()
        self._visible_anim = False
        self._spark = 0.0
        self.hide()

    def _hide_after(self) -> None:
        self._visible_anim = False
        self._spark = 0.0
        self.hide()
        self.strike_finished.emit()

    def _loop_strike(self) -> None:
        if not self._looping:
            return
        self._anim.stop()
        self._anim.setStartValue(-50.0)
        self._anim.setEndValue(5.0)
        self._anim.setDuration(240)

        def _raise() -> None:
            if not self._looping:
                return
            self._anim.setStartValue(5.0)
            self._anim.setEndValue(-50.0)
            self._anim.setDuration(160)
            try:
                self._anim.finished.disconnect()
            except RuntimeError:
                pass
            self._anim.start()

        try:
            self._anim.finished.disconnect()
        except RuntimeError:
            pass
        self._anim.finished.connect(_raise)
        self._anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._visible_anim and self._spark <= 0:
            return
        pal = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        cx, cy = w * 0.55, h * 0.18

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)

        # Wooden handle with rings
        handle_pen = QPen(QColor(pal.wood), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(handle_pen)
        painter.drawLine(0, 0, 0, int(h * 0.28))
        painter.setPen(QPen(QColor(pal.wood).darker(120), 1))
        for t in (0.08, 0.16, 0.22):
            y = int(h * t)
            painter.drawLine(-3, y, 3, y)

        # Metal head with gradient
        head_w, head_h = w * 0.15, h * 0.085
        head_grad = QLinearGradient(-head_w * 0.35, h * 0.24, head_w * 0.65, h * 0.32)
        head_grad.setColorAt(0.0, QColor(pal.metal_light))
        head_grad.setColorAt(0.5, QColor(pal.metal_mid))
        head_grad.setColorAt(1.0, QColor(pal.metal_dark))
        painter.setPen(QPen(QColor(pal.metal_edge), 1))
        painter.setBrush(head_grad)
        painter.drawRoundedRect(
            int(-head_w * 0.35),
            int(h * 0.24),
            int(head_w),
            int(head_h),
            3,
            3,
        )
        # Peen
        painter.setBrush(QColor(pal.metal_mid))
        painter.drawEllipse(
            int(-head_w * 0.48),
            int(h * 0.25),
            int(head_h),
            int(head_h * 0.85),
        )

        painter.restore()

        # Sparks at impact
        if self._spark > 0.05:
            impact_x, impact_y = w * 0.48, h * 0.42
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(10):
                ang = (i / 10.0) * math.pi * 2 + self._spark * 2
                dist = 10 + (1.0 - self._spark) * 32
                sx = impact_x + math.cos(ang) * dist
                sy = impact_y + math.sin(ang) * dist * 0.55
                r = 1.5 + self._spark * 3.5
                color = QColor(pal.ember if i % 2 == 0 else pal.flame_mid)
                color.setAlphaF(min(1.0, self._spark * 1.1))
                painter.setBrush(color)
                painter.drawEllipse(int(sx - r), int(sy - r), int(r * 2), int(r * 2))
            # Brief flash
            flash = QColor(pal.flame_core)
            flash.setAlphaF(self._spark * 0.35)
            painter.setBrush(flash)
            painter.drawEllipse(int(impact_x - 12), int(impact_y - 8), 24, 16)

        painter.end()
