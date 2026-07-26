"""FileForge output slot — finished item ready to download (or cracked on error)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ui.fileforge.theme import ASH, EMBER, ERROR, SPARK, STEEL, SUCCESS


class OutputSlot(QWidget):
    """Minecraft-style result slot: forged item + Download button."""

    download_clicked = Signal()
    download_all_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(160, 180)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._state = "empty"  # empty | ready | error | downloaded
        self._label = ""
        self._detail = ""
        self._ext = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addStretch()

        self.download_btn = QPushButton("Download ⬇️")
        self.download_btn.setObjectName("downloadButton")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_clicked.emit)
        layout.addWidget(self.download_btn)

        self.download_all_btn = QPushButton("Download All")
        self.download_all_btn.setObjectName("downloadButton")
        self.download_all_btn.setEnabled(False)
        self.download_all_btn.clicked.connect(self.download_all_clicked.emit)
        layout.addWidget(self.download_all_btn)

    def set_empty(self) -> None:
        self._state = "empty"
        self._label = ""
        self._detail = ""
        self._ext = ""
        self.download_btn.setEnabled(False)
        self.update()

    def set_ready(self, name: str, ext: str = "", detail: str = "") -> None:
        self._state = "ready"
        self._label = name
        self._ext = ext
        self._detail = detail or "Ready to take"
        self.download_btn.setEnabled(True)
        self.update()

    def set_error(self, name: str, message: str) -> None:
        self._state = "error"
        self._label = name
        self._detail = message
        self._ext = ""
        self.download_btn.setEnabled(False)
        self.update()

    def set_downloaded(self, name: str, path: str = "") -> None:
        self._state = "downloaded"
        self._label = name
        self._detail = path or "Saved"
        self.download_btn.setEnabled(False)
        self.update()

    def set_download_all_enabled(self, enabled: bool) -> None:
        self.download_all_btn.setEnabled(enabled)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        # Slot above buttons (~ leave room for two buttons)
        slot_h = min(100, self.height() - 90)
        slot = QRectF(12, 8, w - 24, slot_h)

        # Outer frame
        painter.setPen(QPen(QColor(EMBER if self._state == "ready" else STEEL), 2))
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(slot, 8, 8)

        title_font = QFont()
        title_font.setPointSize(9)
        painter.setFont(title_font)
        painter.setPen(QColor(ASH))
        painter.drawText(
            QRectF(0, slot.bottom() + 2, w, 14),
            Qt.AlignmentFlag.AlignHCenter,
            "Output slot",
        )

        if self._state == "empty":
            painter.setPen(QColor(ASH))
            painter.drawText(slot, Qt.AlignmentFlag.AlignCenter, "—")
        elif self._state == "ready":
            self._draw_item(painter, slot, cracked=False)
        elif self._state == "error":
            self._draw_item(painter, slot, cracked=True)
        elif self._state == "downloaded":
            self._draw_item(painter, slot, cracked=False, check=True)

        painter.end()

    def _draw_item(
        self,
        painter: QPainter,
        slot: QRectF,
        *,
        cracked: bool,
        check: bool = False,
    ) -> None:
        icon = slot.adjusted(20, 12, -20, -28)
        if cracked:
            painter.setBrush(QColor(ERROR))
        elif check:
            painter.setBrush(QColor(SUCCESS))
        else:
            painter.setBrush(QColor(SPARK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon, 6, 6)

        painter.setPen(QColor("#111"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        if cracked:
            text = "✕"
        elif check:
            text = "✓"
        else:
            text = (self._ext or "OK").upper()[:4]
        painter.drawText(icon, Qt.AlignmentFlag.AlignCenter, text)

        if cracked:
            # Crack lines
            painter.setPen(QPen(QColor("#111"), 2))
            painter.drawLine(
                int(icon.left() + 8),
                int(icon.top() + 6),
                int(icon.center().x()),
                int(icon.bottom() - 8),
            )
            painter.drawLine(
                int(icon.center().x()),
                int(icon.top() + 10),
                int(icon.right() - 6),
                int(icon.bottom() - 6),
            )

        painter.setPen(QColor("#F0E6D8"))
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        name = self._label if len(self._label) <= 18 else self._label[:15] + "…"
        name_rect = QRectF(slot.x(), icon.bottom() + 2, slot.width(), 14)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)
