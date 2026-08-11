"""FileForge anvil — input slot with metallic paint and warm forging glow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ui.fileforge.theme import ScenePalette, ThemeMode, palette_for


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
        self.setMinimumSize(220, 170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Drop a file onto the anvil, or click to browse")

        self._file_name: str = ""
        self._file_ext: str = ""
        self._hover = False
        self._forging = False
        self._palette: ScenePalette = palette_for(ThemeMode.FORGE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    def set_theme(self, mode: ThemeMode | str) -> None:
        self._palette = palette_for(mode)
        self.update()

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
        pal = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        margin_x = w * 0.08
        top = h * 0.18
        face_h = h * 0.30
        base_top = top + face_h + h * 0.04
        base_h = h * 0.16

        # Soft drop shadow under anvil
        shadow = QPainterPath()
        shadow.addEllipse(QRectF(w * 0.22, base_top + base_h - 4, w * 0.56, h * 0.08))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 70))
        painter.drawPath(shadow)

        # Body path (horn + face)
        body = QPainterPath()
        body.moveTo(margin_x + w * 0.05, top + face_h * 0.4)
        body.lineTo(margin_x, top + face_h * 0.15)
        body.lineTo(w * 0.22, top)
        body.lineTo(w * 0.78, top)
        body.lineTo(w - margin_x, top + face_h * 0.15)
        body.lineTo(w - margin_x - w * 0.05, top + face_h * 0.4)
        body.lineTo(w * 0.72, top + face_h)
        body.lineTo(w * 0.28, top + face_h)
        body.closeSubpath()

        base = QPainterPath()
        base.moveTo(w * 0.35, top + face_h)
        base.lineTo(w * 0.65, top + face_h)
        base.lineTo(w * 0.70, base_top + base_h)
        base.lineTo(w * 0.30, base_top + base_h)
        base.closeSubpath()

        # Metal gradients
        body_grad = QLinearGradient(0, top, 0, top + face_h)
        if self._forging:
            body_grad.setColorAt(0.0, QColor(pal.metal_light))
            body_grad.setColorAt(0.35, QColor("#5A4030"))
            body_grad.setColorAt(1.0, QColor(pal.metal_dark))
        elif self._hover:
            body_grad.setColorAt(0.0, QColor(pal.metal_light))
            body_grad.setColorAt(0.5, QColor(pal.metal_mid))
            body_grad.setColorAt(1.0, QColor(pal.metal_dark))
        else:
            body_grad.setColorAt(0.0, QColor(pal.metal_mid))
            body_grad.setColorAt(0.55, QColor(pal.metal_dark))
            body_grad.setColorAt(1.0, QColor(pal.metal_edge))

        painter.fillPath(body, body_grad)
        base_grad = QLinearGradient(0, top + face_h, 0, base_top + base_h)
        base_grad.setColorAt(0.0, QColor(pal.metal_mid))
        base_grad.setColorAt(1.0, QColor(pal.metal_edge))
        painter.fillPath(base, base_grad)

        # Specular highlight on face
        hi = QLinearGradient(w * 0.3, top, w * 0.7, top + face_h * 0.5)
        hi_c = QColor(255, 255, 255, 55 if self._hover or self._forging else 30)
        hi.setColorAt(0.0, hi_c)
        hi.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(hi)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(body)

        # Edge
        edge = QPen(QColor(pal.glow if (self._hover or self._forging) else pal.metal_light))
        edge.setWidth(2)
        painter.setPen(edge)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(body)
        painter.setPen(QPen(QColor(pal.metal_edge), 1.5))
        painter.drawPath(base)

        # Forging heat glow under face
        if self._forging:
            heat = QRadialGradient(w * 0.5, top + face_h * 0.6, w * 0.35)
            hg = QColor(pal.glow)
            hg.setAlpha(80)
            heat.setColorAt(0.0, hg)
            heat.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(heat)
            painter.drawEllipse(QRectF(w * 0.25, top + face_h * 0.2, w * 0.5, face_h * 0.9))

        # Item slot
        slot = QRectF(w * 0.32, top + face_h * 0.15, w * 0.36, face_h * 0.65)
        slot_border = QColor(pal.glow if self._file_name else pal.metal_mid)
        painter.setPen(QPen(slot_border, 2))
        painter.setBrush(QColor(pal.slot_fill))
        painter.drawRoundedRect(slot, 6, 6)

        # Inner bevel
        painter.setPen(QPen(QColor(pal.metal_edge), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(slot.adjusted(2, 2, -2, -2), 4, 4)

        if self._file_name:
            color = QColor(_EXT_COLORS.get(self._file_ext, pal.ember))
            icon = slot.adjusted(10, 8, -10, -22)
            ig = QLinearGradient(icon.topLeft(), icon.bottomRight())
            ig.setColorAt(0.0, color.lighter(120))
            ig.setColorAt(1.0, color.darker(120))
            painter.setBrush(ig)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(icon, 4, 4)

            painter.setPen(QColor("#111"))
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(icon, Qt.AlignmentFlag.AlignCenter, (self._file_ext or "?").upper()[:4])

            painter.setPen(QColor(pal.text))
            font.setPointSize(8)
            font.setBold(False)
            painter.setFont(font)
            name = self._file_name if len(self._file_name) <= 22 else self._file_name[:19] + "…"
            painter.drawText(
                QRectF(slot.x(), slot.bottom() - 16, slot.width(), 14),
                Qt.AlignmentFlag.AlignCenter,
                name,
            )
        else:
            painter.setPen(QColor(pal.text_dim))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(slot, Qt.AlignmentFlag.AlignCenter, "Drop file\non anvil")

        painter.setPen(QColor(pal.text_dim))
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
