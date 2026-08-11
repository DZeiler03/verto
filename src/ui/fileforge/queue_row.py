"""FileForge queue row — inventory-style strip of forge jobs."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
)

from core.conversion_queue import JobStatus
from ui.fileforge.theme import ScenePalette, ThemeMode, palette_for


def _status_color(status: str, pal: ScenePalette) -> QColor:
    mapping = {
        JobStatus.QUEUED.value: pal.metal_mid,
        JobStatus.FORGING.value: pal.accent,
        JobStatus.DONE.value: pal.ember,
        JobStatus.ERROR.value: pal.error,
        JobStatus.CANCELLED.value: pal.ash,
        JobStatus.DOWNLOADED.value: pal.success,
        "ready": pal.metal_mid,
    }
    return QColor(mapping.get(status, pal.metal_mid))


class ForgeItemChip(QWidget):
    """Single inventory cell for a file in the forge queue."""

    selected = Signal(str)

    def __init__(self, job_id: str, name: str, status: str, parent=None) -> None:
        super().__init__(parent)
        self.job_id = job_id
        self._name = name
        self._status = status
        self._active = False
        self._palette: ScenePalette = palette_for(ThemeMode.FORGE)
        self.setFixedSize(76, 76)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{name}\n{status}")

    def set_theme(self, mode: ThemeMode | str) -> None:
        self._palette = palette_for(mode)
        self.update()

    def set_status(self, status: str, detail: str = "") -> None:
        self._status = status
        tip = f"{self._name}\n{status}"
        if detail:
            tip += f"\n{detail}"
        self.setToolTip(tip)
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        pal = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = _status_color(self._status, pal)
        border = QColor(pal.glow if self._active else color)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        # Wood/iron frame
        frame = QLinearGradient(rect.topLeft(), rect.bottomRight())
        frame.setColorAt(0.0, QColor(pal.wood))
        frame.setColorAt(0.4, QColor(pal.metal_dark))
        frame.setColorAt(1.0, QColor(pal.metal_mid))
        painter.setPen(QPen(border, 2 if self._active else 1))
        painter.setBrush(frame)
        painter.drawRoundedRect(rect, 7, 7)

        # Inner plate
        inner = rect.adjusted(4, 4, -4, -4)
        painter.setPen(QPen(QColor(pal.metal_edge), 1))
        painter.setBrush(QColor(pal.panel))
        painter.drawRoundedRect(inner, 4, 4)

        # Status gem with soft glow
        gx, gy, gr = self.width() / 2, 22, 11
        if self._status in {JobStatus.FORGING.value, JobStatus.DONE.value}:
            painter.setPen(Qt.PenStyle.NoPen)
            glow = QColor(color)
            glow.setAlpha(60)
            painter.setBrush(glow)
            painter.drawEllipse(int(gx - gr - 3), int(gy - gr - 3), int((gr + 3) * 2), int((gr + 3) * 2))
        painter.setBrush(color)
        painter.setPen(QPen(QColor(pal.metal_edge), 1))
        painter.drawEllipse(int(gx - gr), int(gy - gr), int(gr * 2), int(gr * 2))

        painter.setPen(QColor(pal.text))
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        name = self._name if len(self._name) <= 10 else self._name[:8] + "…"
        painter.drawText(
            QRectF(4, 38, self.width() - 8, 30),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            f"{name}\n{self._status}",
        )
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.job_id)
        super().mousePressEvent(event)


class ForgeQueueRow(QWidget):
    """Horizontal inventory row of forge queue items with always-visible status."""

    item_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._chips: dict[str, ForgeItemChip] = {}
        self._theme: ThemeMode | str = ThemeMode.FORGE

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(100)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._inner = QWidget()
        self._row = QHBoxLayout(self._inner)
        self._row.setContentsMargins(4, 4, 4, 4)
        self._row.setSpacing(8)
        self._row.addStretch()

        self._scroll.setWidget(self._inner)
        outer.addWidget(self._scroll)

        self._empty_label = QLabel("Forge queue empty — drop files on the anvil")
        self._empty_label.setObjectName("subtitleLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty_label)

    def set_theme(self, mode: ThemeMode | str) -> None:
        self._theme = mode
        for chip in self._chips.values():
            chip.set_theme(mode)
        self.update()

    def clear(self) -> None:
        for chip in self._chips.values():
            self._row.removeWidget(chip)
            chip.deleteLater()
        self._chips.clear()
        self._empty_label.show()
        self._scroll.hide()

    def upsert(
        self,
        job_id: str,
        name: str,
        status: str,
        detail: str = "",
    ) -> None:
        self._empty_label.hide()
        self._scroll.show()
        if job_id in self._chips:
            self._chips[job_id].set_status(status, detail)
        else:
            chip = ForgeItemChip(job_id, name, status)
            chip.set_theme(self._theme)
            chip.selected.connect(self.item_selected.emit)
            self._row.insertWidget(self._row.count() - 1, chip)
            self._chips[job_id] = chip
            if detail:
                chip.set_status(status, detail)

    def set_active(self, job_id: str | None) -> None:
        for jid, chip in self._chips.items():
            chip.set_active(jid == job_id)

    def count(self) -> int:
        return len(self._chips)
