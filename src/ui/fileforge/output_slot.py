"""FileForge output slot — finished item ready to download (or cracked on error)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ui.fileforge.theme import ScenePalette, ThemeMode, palette_for


class OutputSlot(QWidget):
    """Result slot: forged item + Download buttons."""

    download_clicked = Signal()
    download_all_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(160, 190)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._palette: ScenePalette = palette_for(ThemeMode.FORGE)

        self._state = "empty"
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

    def set_theme(self, mode: ThemeMode | str) -> None:
        self._palette = palette_for(mode)
        self.update()

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
        pal = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        slot_h = min(110, self.height() - 90)
        slot = QRectF(12, 8, w - 24, slot_h)

        # Frame with metal bevel
        border_col = (
            pal.glow
            if self._state == "ready"
            else (pal.error if self._state == "error" else pal.metal_mid)
        )
        frame_grad = QLinearGradient(slot.topLeft(), slot.bottomRight())
        frame_grad.setColorAt(0.0, QColor(pal.metal_mid))
        frame_grad.setColorAt(1.0, QColor(pal.metal_dark))
        painter.setPen(QPen(QColor(border_col), 2))
        painter.setBrush(frame_grad)
        painter.drawRoundedRect(slot, 8, 8)

        # Inner cavity
        inner = slot.adjusted(5, 5, -5, -5)
        painter.setPen(QPen(QColor(pal.metal_edge), 1))
        painter.setBrush(QColor(pal.slot_fill))
        painter.drawRoundedRect(inner, 5, 5)

        # Glow ring when ready
        if self._state == "ready":
            painter.setPen(QPen(QColor(pal.glow), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(slot.adjusted(-1, -1, 1, 1), 9, 9)

        painter.setPen(QColor(pal.text_dim))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            QRectF(0, slot.bottom() + 2, w, 14),
            Qt.AlignmentFlag.AlignHCenter,
            "Output slot",
        )

        if self._state == "empty":
            painter.setPen(QColor(pal.text_dim))
            painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, "—")
        elif self._state == "ready":
            self._draw_item(painter, inner, cracked=False)
        elif self._state == "error":
            self._draw_item(painter, inner, cracked=True)
        elif self._state == "downloaded":
            self._draw_item(painter, inner, cracked=False, check=True)

        painter.end()

    def _draw_item(
        self,
        painter: QPainter,
        slot: QRectF,
        *,
        cracked: bool,
        check: bool = False,
    ) -> None:
        pal = self._palette
        icon = slot.adjusted(14, 10, -14, -24)
        if cracked:
            base = QColor(pal.error)
        elif check:
            base = QColor(pal.success)
        else:
            base = QColor(pal.ember)
        grad = QLinearGradient(icon.topLeft(), icon.bottomRight())
        grad.setColorAt(0.0, base.lighter(125))
        grad.setColorAt(1.0, base.darker(115))
        painter.setBrush(grad)
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

        painter.setPen(QColor(pal.text))
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        name = self._label if len(self._label) <= 18 else self._label[:15] + "…"
        painter.drawText(
            QRectF(slot.x(), icon.bottom() + 2, slot.width(), 14),
            Qt.AlignmentFlag.AlignCenter,
            name,
        )
