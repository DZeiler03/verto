"""FileForge queue row — inventory-style strip of forge jobs."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from core.conversion_queue import JobStatus
from ui.fileforge.theme import ASH, EMBER, ERROR, SPARK, STEEL, SUCCESS


_STATUS_COLOR = {
    JobStatus.QUEUED.value: STEEL,
    JobStatus.FORGING.value: EMBER,
    JobStatus.DONE.value: SPARK,
    JobStatus.ERROR.value: ERROR,
    JobStatus.CANCELLED.value: ASH,
    JobStatus.DOWNLOADED.value: SUCCESS,
    "ready": STEEL,
}


class ForgeItemChip(QWidget):
    """Single inventory cell for a file in the forge queue."""

    selected = Signal(str)  # job_id

    def __init__(self, job_id: str, name: str, status: str, parent=None) -> None:
        super().__init__(parent)
        self.job_id = job_id
        self._name = name
        self._status = status
        self._active = False
        self.setFixedSize(72, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{name}\n{status}")

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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(_STATUS_COLOR.get(self._status, STEEL))
        border = QColor(EMBER if self._active else color)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        painter.setPen(QPen(border, 2 if self._active else 1))
        painter.setBrush(QColor(30, 30, 30, 200))
        painter.drawRoundedRect(rect, 6, 6)

        # Status gem
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(self.width() / 2 - 10), 10, 20, 20)

        painter.setPen(QColor("#F0E6D8"))
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        name = self._name if len(self._name) <= 10 else self._name[:8] + "…"
        painter.drawText(
            QRectF(4, 36, self.width() - 8, 28),
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

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(96)
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
            chip.selected.connect(self.item_selected.emit)
            # Insert before trailing stretch
            self._row.insertWidget(self._row.count() - 1, chip)
            self._chips[job_id] = chip
            if detail:
                chip.set_status(status, detail)

    def set_active(self, job_id: str | None) -> None:
        for jid, chip in self._chips.items():
            chip.set_active(jid == job_id)

    def count(self) -> int:
        return len(self._chips)
