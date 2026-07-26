"""Verto main window — FileForge UI with Morphix forge queue (Phase 2 + 3)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.conversion_queue import ConversionJob, ConversionQueue, JobStatus
from core.settings import AppSettings, load_settings, save_settings
from core.storage import SaveDestination, StorageManager
from morphix.base import GOOGLE_POINTER_MESSAGE, output_extension
from morphix.engine import MorphixEngine
from ui.fileforge import (
    AnvilWidget,
    ForgeQueueRow,
    HammerOverlay,
    OutputSlot,
    ThemeMode,
    stylesheet,
)
from ui.settings_dialog import SettingsDialog
from utils.paths import downloads_dir

logger = logging.getLogger("verto.ui")


class ConversionWorker(QObject):
    """Runs Morphix conversion jobs off the UI thread."""

    job_updated = Signal(object)  # ConversionJob
    finished = Signal()
    batch_done = Signal()

    def __init__(self, queue: ConversionQueue) -> None:
        super().__init__()
        self.queue = queue
        self.queue.set_progress_callback(self._on_progress)

    def _on_progress(self, job: ConversionJob) -> None:
        self.job_updated.emit(job)

    @Slot()
    def run(self) -> None:
        try:
            self.queue.process_all_sync()
        finally:
            self.batch_done.emit()
            self.finished.emit()


class MainWindow(QMainWindow):
    """Verto application window with FileForge theming."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Verto")
        self.resize(860, 640)

        self.settings: AppSettings = load_settings()
        self.engine = MorphixEngine()
        self.storage = StorageManager(
            destination=self.settings.destination_enum,
            custom_dir=Path(self.settings.custom_save_dir)
            if self.settings.custom_save_dir
            else None,
        )
        purged = self.storage.cleanup_stale_on_startup()
        if purged:
            logger.info("Purged %d stale staged file(s) on startup", purged)

        self.queue = ConversionQueue(self.engine)
        self._jobs_by_id: dict[str, ConversionJob] = {}
        self._source_entries: list[Path] = []  # files waiting to be forged
        self._active_job_id: str | None = None
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None
        self._busy = False

        self._build_menu()
        self._build_ui()
        self.apply_theme(self.settings.theme)
        self._update_status_ready()

    # ── UI construction ──────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        act_add = QAction("Add files…", self)
        act_add.triggered.connect(self._browse_files)
        file_menu.addAction(act_add)
        act_settings = QAction("Settings…", self)
        act_settings.triggered.connect(self._open_settings)
        file_menu.addAction(act_settings)
        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        tools_menu = menu.addMenu("&Tools")
        act_pdf = QAction("PDF tools (merge / split / compress)…", self)
        act_pdf.triggered.connect(self._open_pdf_tools)
        tools_menu.addAction(act_pdf)

        view_menu = menu.addMenu("&View")
        act_forge = QAction("Forge theme (dark)", self)
        act_forge.triggered.connect(lambda: self._set_theme(ThemeMode.FORGE.value))
        act_day = QAction("Daylight smithy (light)", self)
        act_day.triggered.connect(lambda: self._set_theme(ThemeMode.DAYLIGHT.value))
        view_menu.addAction(act_forge)
        view_menu.addAction(act_day)

        help_menu = menu.addMenu("&Help")
        act_about = QAction("About Verto", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Verto")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Offline file converter · Morphix engine under the hood · FileForge smithy"
        )
        subtitle.setObjectName("subtitleLabel")
        root.addWidget(title)
        root.addWidget(subtitle)

        # Forge floor: anvil + hammer overlay + format + output
        forge_row = QHBoxLayout()
        forge_row.setSpacing(16)

        anvil_wrap = QWidget()
        anvil_layout = QVBoxLayout(anvil_wrap)
        anvil_layout.setContentsMargins(0, 0, 0, 0)
        self.anvil = AnvilWidget()
        self.anvil.files_dropped.connect(self._on_files_dropped)
        self.anvil.clicked.connect(lambda: None)  # browse via empty drop signal
        anvil_layout.addWidget(self.anvil)

        # Hammer overlay parented to anvil wrap, sized over anvil
        self.hammer = HammerOverlay(anvil_wrap)
        self.anvil.installEventFilter(self)

        forge_row.addWidget(anvil_wrap, stretch=2)

        mid = QVBoxLayout()
        mid.addStretch()
        fmt_label = QLabel("Target format")
        fmt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mid.addWidget(fmt_label)
        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(110)
        mid.addWidget(self.format_combo)
        mid.addSpacing(12)
        self.forge_btn = QPushButton("Forge it! 🔨")
        self.forge_btn.setObjectName("forgeButton")
        self.forge_btn.clicked.connect(self._start_conversion)
        mid.addWidget(self.forge_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_forging)
        mid.addWidget(self.cancel_btn)
        mid.addStretch()
        forge_row.addLayout(mid)

        self.output_slot = OutputSlot()
        self.output_slot.download_clicked.connect(self._download_active)
        self.output_slot.download_all_clicked.connect(self._download_all)
        forge_row.addWidget(self.output_slot)

        root.addLayout(forge_row)

        # Status detail always visible
        self.detail_label = QLabel("Ready — drop a file on the anvil to begin")
        self.detail_label.setObjectName("statusDetail")
        self.detail_label.setWordWrap(True)
        root.addWidget(self.detail_label)

        # Forge queue inventory row
        queue_label = QLabel("Forge queue")
        root.addWidget(queue_label)
        self.queue_row = ForgeQueueRow()
        self.queue_row.item_selected.connect(self._on_queue_item_selected)
        root.addWidget(self.queue_row)

        # Bottom actions
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add files…")
        self.add_btn.clicked.connect(self._browse_files)
        self.clear_btn = QPushButton("Clear queue")
        self.clear_btn.clicked.connect(self._clear)
        self.settings_btn = QPushButton("Settings…")
        self.settings_btn.clicked.connect(self._open_settings)
        self.open_out_btn = QPushButton("Open Downloads")
        self.open_out_btn.clicked.connect(self._open_downloads)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.settings_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.open_out_btn)
        root.addLayout(btn_row)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def eventFilter(self, obj, event):  # noqa: N802
        # Keep hammer overlay geometry aligned with anvil
        if obj is self.anvil:
            from PySide6.QtCore import QEvent

            if event.type() in {
                QEvent.Type.Resize,
                QEvent.Type.Move,
                QEvent.Type.Show,
            }:
                self.hammer.setGeometry(self.anvil.geometry())
        return super().eventFilter(obj, event)

    def apply_theme(self, mode: str) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet(mode))
        self.settings.theme = mode

    def _set_theme(self, mode: str) -> None:
        self.apply_theme(mode)
        save_settings(self.settings)

    # ── File intake ──────────────────────────────────────────────────

    @Slot(list)
    def _on_files_dropped(self, paths: list) -> None:
        if not paths:
            self._browse_files()
            return
        self._add_paths([Path(p) for p in paths])

    def _browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add files to the forge",
            str(Path.home()),
            "All files (*.*)",
        )
        if files:
            self._add_paths([Path(f) for f in files])

    def _add_paths(self, paths: list[Path]) -> None:
        large: list[str] = []
        threshold = self.settings.large_file_threshold_bytes

        for path in paths:
            if not path.is_file():
                continue
            info = self.engine.detect(path)
            if info.is_google_pointer:
                QMessageBox.warning(
                    self,
                    "Google Drive link file",
                    GOOGLE_POINTER_MESSAGE,
                )
                self.queue_row.upsert(
                    f"skip-{path.name}",
                    path.name,
                    JobStatus.ERROR.value,
                    "Google Drive link file",
                )
                continue
            if not info.readable:
                QMessageBox.warning(
                    self,
                    "Cannot read file",
                    info.detail or f"Cannot read {path.name}",
                )
                continue

            try:
                size = path.stat().st_size
                if self.settings.warn_large_files and size >= threshold:
                    large.append(f"{path.name} ({size / (1024 * 1024):.1f} MiB)")
            except OSError:
                pass

            if path not in self._source_entries:
                self._source_entries.append(path)
            self.queue_row.upsert(
                f"src-{path.resolve()}",
                path.name,
                "ready",
                info.category.value,
            )
            # Show last added on anvil
            self.anvil.set_file(path)

        if large:
            QMessageBox.warning(
                self,
                "Large file(s)",
                "These files are large and may take a while or use significant disk space:\n\n"
                + "\n".join(large)
                + "\n\nYou can still forge them.",
            )

        self._refresh_formats()
        self._update_detail(
            f"{len(self._source_entries)} file(s) on the forge — pick a format and strike"
        )

    def _refresh_formats(self) -> None:
        current = self.format_combo.currentData()
        self.format_combo.clear()
        if not self._source_entries:
            return
        target_sets = [set(self.engine.list_target_formats(s)) for s in self._source_entries]
        common = set.intersection(*target_sets) if len(target_sets) > 1 else target_sets[0]
        # Friendly labels for special Morphix ops
        labels = {
            "pdf-compressed": "PDF (compress)",
            "pdf-split": "PDF (split pages)",
            "ocr-txt": "TXT (OCR)",
        }
        for fmt in sorted(common):
            self.format_combo.addItem(labels.get(fmt, fmt.upper()), fmt)
        if current:
            idx = self.format_combo.findData(current)
            if idx >= 0:
                self.format_combo.setCurrentIndex(idx)
        if self.format_combo.count() == 0:
            self._update_detail("No common target formats for the selected files")

    # ── Conversion (Morphix) ─────────────────────────────────────────

    def _start_conversion(self) -> None:
        if self._busy:
            return
        if not self._source_entries:
            QMessageBox.information(self, "Verto", "Drop at least one file on the anvil first.")
            return
        target = self.format_combo.currentData()
        if not target:
            QMessageBox.information(
                self,
                "Verto",
                "No target format available for the selected file(s).",
            )
            return

        # Build queue — results stay in staging until Download
        self.queue = ConversionQueue(self.engine)
        self._jobs_by_id.clear()
        real_ext = output_extension(target)
        for src in self._source_entries:
            staged = self.storage.make_staging_path(real_ext, stem=src.stem)
            job = self.queue.add(src, target, staged)
            self._jobs_by_id[job.id] = job
            self.queue_row.upsert(job.id, src.name, JobStatus.QUEUED.value)

        self._set_busy(True)
        self.anvil.set_forging(True)
        self.hammer.setGeometry(self.anvil.geometry())
        self.hammer.start_loop()
        self._update_detail("Forging… Morphix is converting in the background")
        self.status.showMessage("Morphix at work — please wait")

        self._thread = QThread()
        self._worker = ConversionWorker(self.queue)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.job_updated.connect(self._on_job_updated)
        self._worker.batch_done.connect(self._on_batch_done)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _cancel_forging(self) -> None:
        if not self._busy:
            return
        self.queue.stop()
        self.queue.cancel_pending()
        self._update_detail("Cancel requested — finishing current strike, then stopping")

    @Slot(object)
    def _on_job_updated(self, job: ConversionJob) -> None:
        self._jobs_by_id[job.id] = job
        detail = ""
        if job.status == JobStatus.ERROR:
            detail = job.error_message
        elif job.status == JobStatus.DONE:
            detail = "Staged — click Download to save"
        elif job.status == JobStatus.FORGING:
            detail = "Hammering…"
        elif job.status == JobStatus.CANCELLED:
            detail = "Cancelled"

        self.queue_row.upsert(job.id, job.display_name, job.status.value, detail)
        self.queue_row.set_active(job.id)
        self._active_job_id = job.id
        self.anvil.set_file(job.source)

        if job.status == JobStatus.DONE:
            ext = output_extension(job.target_format)
            self.output_slot.set_ready(
                f"{job.source.stem}.{ext}",
                ext=ext,
                detail="Forged — ready to download",
            )
            self._update_detail(f"Forged {job.display_name} → .{ext} (still in staging)")
        elif job.status == JobStatus.ERROR:
            self.output_slot.set_error(job.display_name, job.error_message)
            self._update_detail(f"Error: {job.error_message}")
        elif job.status == JobStatus.FORGING:
            self._update_detail(f"Forging {job.display_name}…")

        self._refresh_download_all()

    @Slot()
    def _on_batch_done(self) -> None:
        jobs = self.queue.jobs
        done = sum(1 for j in jobs if j.status == JobStatus.DONE)
        errors = sum(1 for j in jobs if j.status == JobStatus.ERROR)
        cancelled = sum(1 for j in jobs if j.status == JobStatus.CANCELLED)

        success = done > 0 and errors == 0
        self.hammer.stop_with_finale(success=done > 0)
        self.anvil.set_forging(False)
        self._set_busy(False)

        # Keep sources that failed so user can retry; clear successful sources
        # Files stay in queue as forged items until downloaded/cleared
        self._source_entries.clear()
        self._refresh_formats()
        self._refresh_download_all()

        msg = f"Done — {done} forged, {errors} failed"
        if cancelled:
            msg += f", {cancelled} cancelled"
        msg += " · use Download to save staged files"
        self.status.showMessage(msg)
        self._update_detail(msg)

        if errors and done == 0 and cancelled == 0:
            first = next(j for j in jobs if j.status == JobStatus.ERROR)
            QMessageBox.warning(
                self,
                "Forging failed",
                first.error_message or "Unknown error",
            )

    # ── Download (Phase 2 staging → user destination) ────────────────

    def _refresh_download_all(self) -> None:
        ready = [j for j in self._jobs_by_id.values() if j.is_ready_to_download]
        self.output_slot.set_download_all_enabled(len(ready) > 0)
        if self._active_job_id:
            job = self._jobs_by_id.get(self._active_job_id)
            if job and job.is_ready_to_download:
                self.output_slot.download_btn.setEnabled(True)
            elif job and job.is_downloaded:
                self.output_slot.download_btn.setEnabled(False)

    def _on_queue_item_selected(self, job_id: str) -> None:
        self._active_job_id = job_id
        self.queue_row.set_active(job_id)
        job = self._jobs_by_id.get(job_id)
        if not job:
            # Source-only chip before forging
            return
        self.anvil.set_file(job.source)
        if job.status == JobStatus.DONE:
            ext = output_extension(job.target_format)
            self.output_slot.set_ready(
                f"{job.source.stem}.{ext}",
                ext=ext,
            )
            self._update_detail(f"Selected {job.display_name} — ready to download")
        elif job.status == JobStatus.ERROR:
            self.output_slot.set_error(job.display_name, job.error_message)
            self._update_detail(job.error_message)
        elif job.status == JobStatus.DOWNLOADED:
            path = str(job.downloaded_path or "")
            self.output_slot.set_downloaded(job.display_name, path)
            self._update_detail(f"Already downloaded to {path}")
        else:
            self.output_slot.set_empty()
            self._update_detail(f"{job.display_name}: {job.status.value}")
        self._refresh_download_all()

    def _resolve_destination(self, job: ConversionJob) -> Path | None:
        ext = output_extension(job.target_format)
        if self.storage.needs_save_dialog():
            suggested = str(
                self.storage.resolve_save_path(job.source, ext)
            )
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save forged file",
                suggested,
                f"*.{ext};;All files (*.*)",
            )
            if not path:
                return None
            return Path(path)
        return self.storage.resolve_save_path(job.source, ext)

    def _download_job(self, job: ConversionJob) -> bool:
        if not job.is_ready_to_download or not job.result:
            return False
        dest = self._resolve_destination(job)
        if dest is None:
            return False
        try:
            paths = job.result.all_outputs
            primary = self.storage.promote(paths[0], dest)
            extras_saved: list[Path] = []
            for extra in paths[1:]:
                extras_saved.append(
                    self.storage.promote(extra, dest.parent / extra.name)
                )
            self.queue.mark_downloaded(job.id, primary, extras_saved)
            job.status = JobStatus.DOWNLOADED
            job.downloaded_path = primary
            self._jobs_by_id[job.id] = job
            self.queue_row.upsert(
                job.id,
                job.display_name,
                JobStatus.DOWNLOADED.value,
                str(primary),
            )
            self.output_slot.set_downloaded(job.display_name, str(primary))
            self._update_detail(f"Downloaded → {primary}")
            return True
        except OSError as exc:
            QMessageBox.warning(self, "Download failed", str(exc))
            return False

    def _download_active(self) -> None:
        job = self._jobs_by_id.get(self._active_job_id or "")
        if not job:
            # Prefer first ready job
            ready = [j for j in self._jobs_by_id.values() if j.is_ready_to_download]
            if not ready:
                QMessageBox.information(self, "Verto", "Nothing ready to download yet.")
                return
            job = ready[-1]
        self._download_job(job)
        self._refresh_download_all()

    def _download_all(self) -> None:
        ready = [j for j in self._jobs_by_id.values() if j.is_ready_to_download]
        if not ready:
            QMessageBox.information(self, "Verto", "No forged files waiting in staging.")
            return
        ok = 0
        for job in ready:
            if self._download_job(job):
                ok += 1
        self._refresh_download_all()
        self.status.showMessage(f"Downloaded {ok} / {len(ready)} file(s)")
        if ok:
            QMessageBox.information(
                self,
                "Download complete",
                f"Saved {ok} file(s).\nDestination: {self.storage.destination_label()}",
            )

    # ── Misc ─────────────────────────────────────────────────────────

    def _clear(self) -> None:
        if self._busy:
            return
        self._source_entries.clear()
        self._jobs_by_id.clear()
        self.queue = ConversionQueue(self.engine)
        self.queue_row.clear()
        self.anvil.clear()
        self.output_slot.set_empty()
        self.output_slot.set_download_all_enabled(False)
        self.format_combo.clear()
        self.hammer.stop_immediate()
        self._update_status_ready()
        self._update_detail("Queue cleared")

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings = dlg.result_settings()
            save_settings(self.settings)
            self.storage.apply_prefs(
                self.settings.destination_enum,
                self.settings.custom_save_dir or None,
            )
            self.apply_theme(self.settings.theme)
            self._update_status_ready()

    def _open_pdf_tools(self) -> None:
        from ui.pdf_tools_dialog import PdfToolsDialog

        dlg = PdfToolsDialog(self.engine, self.storage, self)
        dlg.exec()

    def _open_downloads(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(downloads_dir())))

    def _about(self) -> None:
        lo = "found" if self.engine.libreoffice_available() else "not found"
        ocr = "found" if self.engine.ocr_available() else "not found"
        QMessageBox.about(
            self,
            "About Verto",
            "<h3>Verto</h3>"
            "<p>Offline desktop file converter (Linux-first).</p>"
            "<p><b>Morphix</b> handles all format detection and conversion work "
            "under the hood — including PDF merge/split/compress and optional OCR.</p>"
            "<p><b>FileForge</b> is the anvil / hammer visual theme.</p>"
            f"<p>LibreOffice: {lo}<br>Tesseract OCR: {ocr}<br>No network · No telemetry</p>",
        )

    def _update_status_ready(self) -> None:
        lo = "LO✓" if self.engine.libreoffice_available() else "LO✗"
        ocr = "OCR✓" if self.engine.ocr_available() else "OCR✗"
        dest = self.storage.destination_label()
        self.status.showMessage(f"Ready · offline · {lo} · {ocr} · save: {dest}")

    def _update_detail(self, text: str) -> None:
        self.detail_label.setText(text)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.forge_btn.setEnabled(not busy)
        self.add_btn.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.format_combo.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.anvil.setEnabled(not busy)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._busy:
            self.queue.stop()
            self.queue.cancel_pending()
        try:
            self.storage.cleanup_all_on_exit()
        except Exception:  # noqa: BLE001
            logger.exception("Staging cleanup on exit failed")
        save_settings(self.settings)
        super().closeEvent(event)
