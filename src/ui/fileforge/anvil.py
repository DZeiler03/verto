"""FileForge anvil — input slot for files (drag-drop / click to browse)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ui.fileforge.theme import ANVIL, ASH, EMBER, EMBER_GLOW, SPARK, STEEL


_EXT_COLORS = {
    "pdf": "#E53935",
    "png": "#43A047",
    "jpg": "#1E88E5",
    "jpeg": "#1E88E5",
    "gif": "#8E24AA",
    "webp": "#00ACC1",
    "bmp": "#6D4C41",
    "tiff": "#5E35B1",
    "tif": "#5E35B1",
    "docx": "#1565C0",
    "xlsx": "#2E7D32",
    "pptx": "#E65100",
    "csv": "#558B2F",
    "txt": "#78909C",
    "odt": "#0277BD",
    "ods": "#558B2F",
    "odp": "#EF6C00",
}


class AnvilWidget(QWidget):
    """Central anvil input slot — drop or click to place a file."""

    files_dropped = Signal(list)  # list[str]
    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(220, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Drop a file onto the anvil, or click to browse")

        self._file_name: str = ""
        self._file_ext: str = ""
        self._hover = False
        self._forging = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    def set_file(self, path: Path | str | None) -> None:
        if path is None:
            self._file_name = ""
            self._file_ext = ""
        else:
            p = Path(path)
            self._file_name = p.name
            self._file_ext = p.suffix.lstrip(".").lower()
        self.update()

    def set_forging(self, forging: bool) -> None:
        self._forging = forging
        self.update()

    def clear(self) -> None:
        self.set_file(None)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        # Anvil body
        body = QPainterPath()
        # Horn + face silhouette
        margin_x = w * 0.08
        top = h * 0.22
        face_h = h * 0.28
        base_top = top + face_h + h * 0.05
        base_h = h * 0.18

        # Top face (flat work surface)
        body.moveTo(margin_x + w * 0.05, top + face_h * 0.4)
        body.lineTo(margin_x, top + face_h * 0.15)
        body.lineTo(w * 0.22, top)
        body.lineTo(w * 0.78, top)
        body.lineTo(w - margin_x, top + face_h * 0.15)
        body.lineTo(w - margin_x - w * 0.05, top + face_h * 0.4)
        body.lineTo(w * 0.72, top + face_h)
        body.lineTo(w * 0.28, top + face_h)
        body.closeSubpath()

        # Waist / base
        base = QPainterPath()
        base.moveTo(w * 0.35, top + face_h)
        base.lineTo(w * 0.65, top + face_h)
        base.lineTo(w * 0.70, base_top + base_h)
        base.lineTo(w * 0.30, base_top + base_h)
        base.closeSubpath()

        anvil_color = QColor(ANVIL)
        if self._hover:
            anvil_color = QColor(STEEL)
        if self._forging:
            anvil_color = QColor("#3A2820")

        painter.fillPath(body, anvil_color)
        painter.fillPath(base, QColor("#252525"))

        border = QPen(QColor(EMBER if (self._hover or self._forging) else ASH))
        border.setWidth(2)
        painter.setPen(border)
        painter.drawPath(body)
        painter.drawPath(base)

        # Item slot on the face
        slot = QRectF(w * 0.32, top + face_h * 0.15, w * 0.36, face_h * 0.65)
        painter.setPen(QPen(QColor(EMBER_GLOW if self._file_name else STEEL), 2))
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.drawRoundedRect(slot, 6, 6)

        if self._file_name:
            # File-type "item" icon block
            color = QColor(_EXT_COLORS.get(self._file_ext, SPARK))
            icon = slot.adjusted(10, 8, -10, -22)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(icon, 4, 4)

            painter.setPen(QColor("#111"))
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            label = (self._file_ext or "?").upper()[:4]
            painter.drawText(icon, Qt.AlignmentFlag.AlignCenter, label)

            painter.setPen(QColor("#F0E6D8"))
            font.setPointSize(8)
            font.setBold(False)
            painter.setFont(font)
            name = self._file_name if len(self._file_name) <= 22 else self._file_name[:19] + "…"
            name_rect = QRectF(slot.x(), slot.bottom() - 16, slot.width(), 14)
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)
        else:
            painter.setPen(QColor(ASH))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(slot, Qt.AlignmentFlag.AlignCenter, "Drop file\non anvil")

        # Caption under anvil
        painter.setPen(QColor(ASH))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        caption = "Forging…" if self._forging else "The Anvil — input slot"
        painter.drawText(
            QRectF(0, base_top + base_h + 4, w, 18),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            caption,
        )

        painter.end()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            self.files_dropped.emit([])
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._hover = True
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths:
            self.files_dropped.emit(paths)
        self._hover = False
        self.update()
        event.acceptProposedAction()
