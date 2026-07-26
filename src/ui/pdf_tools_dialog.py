"""PDF tools dialog — merge, split, compress via Morphix (offline)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.storage import StorageManager
from morphix.base import ConversionError
from morphix.engine import MorphixEngine

logger = logging.getLogger("verto.ui.pdf_tools")


class PdfToolsDialog(QDialog):
    """Modal tools for multi-file PDF operations."""

    def __init__(
        self,
        engine: MorphixEngine,
        storage: StorageManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.storage = storage
        self.setWindowTitle("PDF Tools — Morphix")
        self.setMinimumSize(520, 400)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._merge_tab(), "Merge")
        tabs.addTab(self._split_tab(), "Split")
        tabs.addTab(self._compress_tab(), "Compress")
        root.addWidget(tabs)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        close.accepted.connect(self.accept)
        root.addWidget(close)

    def _merge_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Select two or more PDFs to forge into one file."))
        self.merge_list = QListWidget()
        layout.addWidget(self.merge_list)
        row = QHBoxLayout()
        add = QPushButton("Add PDFs…")
        add.clicked.connect(self._merge_add)
        up = QPushButton("Move up")
        up.clicked.connect(lambda: self._move_item(self.merge_list, -1))
        down = QPushButton("Move down")
        down.clicked.connect(lambda: self._move_item(self.merge_list, 1))
        rem = QPushButton("Remove")
        rem.clicked.connect(lambda: self._remove_selected(self.merge_list))
        row.addWidget(add)
        row.addWidget(up)
        row.addWidget(down)
        row.addWidget(rem)
        layout.addLayout(row)
        run = QPushButton("Merge & stage for Download")
        run.setObjectName("forgeButton")
        run.clicked.connect(self._run_merge)
        layout.addWidget(run)
        return w

    def _split_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Split a PDF into one file per page."))
        form = QFormLayout()
        self.split_path = QLabel("(no file)")
        self._split_file: Path | None = None
        pick = QPushButton("Choose PDF…")
        pick.clicked.connect(self._pick_split)
        form.addRow("Source:", self.split_path)
        form.addRow("", pick)
        layout.addLayout(form)
        run = QPushButton("Split & stage for Download")
        run.setObjectName("forgeButton")
        run.clicked.connect(self._run_split)
        layout.addWidget(run)
        layout.addStretch()
        return w

    def _compress_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Compress a PDF (local re-encode via Morphix / PyMuPDF)."))
        form = QFormLayout()
        self.compress_path = QLabel("(no file)")
        self._compress_file: Path | None = None
        pick = QPushButton("Choose PDF…")
        pick.clicked.connect(self._pick_compress)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 200)
        self.dpi_spin.setValue(100)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(40, 95)
        self.quality_spin.setValue(70)
        form.addRow("Source:", self.compress_path)
        form.addRow("", pick)
        form.addRow("Target DPI:", self.dpi_spin)
        form.addRow("JPEG quality:", self.quality_spin)
        layout.addLayout(form)
        run = QPushButton("Compress & stage for Download")
        run.setObjectName("forgeButton")
        run.clicked.connect(self._run_compress)
        layout.addWidget(run)
        layout.addStretch()
        return w

    def _merge_add(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add PDFs", str(Path.home()), "PDF (*.pdf)"
        )
        for f in files:
            self.merge_list.addItem(f)

    def _pick_split(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, "PDF to split", str(Path.home()), "PDF (*.pdf)"
        )
        if f:
            self._split_file = Path(f)
            self.split_path.setText(self._split_file.name)

    def _pick_compress(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, "PDF to compress", str(Path.home()), "PDF (*.pdf)"
        )
        if f:
            self._compress_file = Path(f)
            self.compress_path.setText(self._compress_file.name)

    def _move_item(self, list_w: QListWidget, delta: int) -> None:
        row = list_w.currentRow()
        if row < 0:
            return
        new = row + delta
        if new < 0 or new >= list_w.count():
            return
        item = list_w.takeItem(row)
        list_w.insertItem(new, item)
        list_w.setCurrentRow(new)

    def _remove_selected(self, list_w: QListWidget) -> None:
        for item in list_w.selectedItems():
            list_w.takeItem(list_w.row(item))

    def _run_merge(self) -> None:
        paths = [Path(self.merge_list.item(i).text()) for i in range(self.merge_list.count())]
        if len(paths) < 2:
            QMessageBox.information(self, "Merge", "Add at least two PDFs.")
            return
        staged = self.storage.make_staging_path("pdf", stem="merged")
        try:
            result = self.engine.merge_pdfs(paths, staged)
            dest = self.storage.resolve_save_path(paths[0], "pdf")
            # suggest name merged
            dest = dest.with_name(f"merged_{paths[0].stem}.pdf")
            if self.storage.needs_save_dialog():
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save merged PDF", str(dest), "PDF (*.pdf)"
                )
                if not path:
                    QMessageBox.information(
                        self, "Staged", f"Merged PDF is in staging:\n{result.output_path}"
                    )
                    return
                dest = Path(path)
            saved = self.storage.promote(result.output_path, dest)
            QMessageBox.information(self, "Merged", f"{result.message}\nSaved to:\n{saved}")
        except ConversionError as exc:
            QMessageBox.warning(self, "Merge failed", exc.user_message)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Merge failed", str(exc))

    def _run_split(self) -> None:
        if not self._split_file:
            QMessageBox.information(self, "Split", "Choose a PDF first.")
            return
        out_dir = self.storage.staging_root / f"{self._split_file.stem}_pages"
        try:
            result = self.engine.split_pdf(self._split_file, out_dir)
            # Promote all pages to downloads folder
            dest_dir = self.storage.resolve_save_path(self._split_file, "pdf").parent
            saved = []
            for p in result.all_outputs:
                saved.append(self.storage.promote(p, dest_dir / p.name))
            QMessageBox.information(
                self,
                "Split",
                f"{result.message}\nSaved {len(saved)} file(s) to:\n{dest_dir}",
            )
        except ConversionError as exc:
            QMessageBox.warning(self, "Split failed", exc.user_message)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Split failed", str(exc))

    def _run_compress(self) -> None:
        if not self._compress_file:
            QMessageBox.information(self, "Compress", "Choose a PDF first.")
            return
        staged = self.storage.make_staging_path("pdf", stem=f"{self._compress_file.stem}_compressed")
        try:
            result = self.engine.compress_pdf(
                self._compress_file,
                staged,
                {"dpi": self.dpi_spin.value(), "quality": self.quality_spin.value()},
            )
            dest = self.storage.resolve_save_path(self._compress_file, "pdf")
            dest = dest.with_name(f"{self._compress_file.stem}_compressed.pdf")
            if self.storage.needs_save_dialog():
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save compressed PDF", str(dest), "PDF (*.pdf)"
                )
                if not path:
                    QMessageBox.information(
                        self, "Staged", f"Compressed PDF in staging:\n{result.output_path}"
                    )
                    return
                dest = Path(path)
            saved = self.storage.promote(result.output_path, dest)
            QMessageBox.information(self, "Compressed", f"{result.message}\nSaved to:\n{saved}")
        except ConversionError as exc:
            QMessageBox.warning(self, "Compress failed", exc.user_message)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Compress failed", str(exc))
