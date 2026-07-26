"""Reusable Phase 1 UI widgets for Verto."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DropZone(QWidget):
    """Clickable / drag-and-drop area for adding files to the forge queue."""

    files_dropped = Signal(list)  # list[str] paths

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            """
            DropZone {
                border: 2px dashed #888;
                border-radius: 8px;
                background: #f7f7f7;
            }
            DropZone:hover {
                border-color: #E85D04;
                background: #fff8f0;
            }
            """
        )
        layout = QVBoxLayout(self)
        self._label = QLabel("Drop files here\nor click to browse")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #444; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(self._label)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.files_dropped.emit([])  # empty list → parent opens dialog
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


class FileQueueList(QListWidget):
    """Shows files in the forge queue with status text."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self._job_ids: dict[str, QListWidgetItem] = {}

    def upsert_job(
        self,
        job_id: str,
        name: str,
        status: str,
        detail: str = "",
    ) -> None:
        text = f"{name}  —  {status}"
        if detail:
            text += f"  ({detail})"
        if job_id in self._job_ids:
            self._job_ids[job_id].setText(text)
            self._job_ids[job_id].setData(Qt.ItemDataRole.UserRole, job_id)
        else:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, job_id)
            item.setToolTip(detail or name)
            self.addItem(item)
            self._job_ids[job_id] = item

    def clear_jobs(self) -> None:
        self.clear()
        self._job_ids.clear()
