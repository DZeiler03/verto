"""FileForge hammer-strike animation over the anvil."""

from __future__ import annotations

import math

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTransform
from PySide6.QtWidgets import QWidget

from ui.fileforge.theme import EMBER, HAMMER, SPARK


class HammerOverlay(QWidget):
    """Animated hammer that loops while forging, then plays a final strike + sparks."""

    strike_finished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._angle = -40.0  # degrees; more negative = raised
        self._spark = 0.0  # 0..1 spark intensity
        self._visible_anim = False
        self._looping = False

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
        """Loop hammer strikes until stop_with_finale()."""
        self._looping = True
        self._visible_anim = True
        self.show()
        self.raise_()
        self._loop_strike()
        self._loop_timer.start()

    def stop_with_finale(self, success: bool = True) -> None:
        """Stop the loop and play a final impact (with sparks on success)."""
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        # Pivot near top-center of anvil face
        cx, cy = w * 0.55, h * 0.18

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)

        # Handle
        painter.setPen(QPen(QColor("#5D4037"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(0, 0, 0, int(h * 0.28))

        # Head
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(HAMMER))
        head_w, head_h = w * 0.14, h * 0.08
        painter.drawRoundedRect(int(-head_w * 0.35), int(h * 0.24), int(head_w), int(head_h), 3, 3)
        # Peen
        painter.setBrush(QColor("#9E9E9E"))
        painter.drawEllipse(int(-head_w * 0.45), int(h * 0.25), int(head_h), int(head_h * 0.8))

        painter.restore()

        # Sparks at impact point
        if self._spark > 0.05:
            impact_x, impact_y = w * 0.48, h * 0.42
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(8):
                ang = (i / 8.0) * math.pi * 2 + self._spark
                dist = 12 + (1.0 - self._spark) * 28
                sx = impact_x + math.cos(ang) * dist
                sy = impact_y + math.sin(ang) * dist * 0.6
                r = 2 + self._spark * 3
                color = QColor(SPARK if i % 2 == 0 else EMBER)
                color.setAlphaF(self._spark)
                painter.setBrush(color)
                painter.drawEllipse(int(sx - r), int(sy - r), int(r * 2), int(r * 2))

        painter.end()
