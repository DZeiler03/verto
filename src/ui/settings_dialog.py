"""Preferences dialog — save destination + FileForge theme."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from core.settings import AppSettings
from core.storage import SaveDestination
from ui.fileforge.theme import ThemeMode


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Verto Settings")
        self.setMinimumWidth(440)
        self._settings = settings
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)

        # Save destination
        dest_box = QGroupBox("Download destination")
        dest_layout = QVBoxLayout(dest_box)
        self._dest_group = QButtonGroup(self)
        self._radio_downloads = QRadioButton("Always save to Downloads (default)")
        self._radio_next = QRadioButton("Always save next to the original source file")
        self._radio_ask = QRadioButton("Always ask (Save As dialog every time)")
        self._radio_custom = QRadioButton("Custom fixed folder:")
        for i, r in enumerate(
            (self._radio_downloads, self._radio_next, self._radio_ask, self._radio_custom)
        ):
            self._dest_group.addButton(r, i)
            dest_layout.addWidget(r)

        custom_row = QHBoxLayout()
        self._custom_edit = QLineEdit(self._settings.custom_save_dir)
        self._custom_edit.setPlaceholderText("Choose a folder…")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_custom)
        custom_row.addWidget(self._custom_edit)
        custom_row.addWidget(browse)
        dest_layout.addLayout(custom_row)
        root.addWidget(dest_box)

        dest = self._settings.destination_enum
        {
            SaveDestination.DOWNLOADS: self._radio_downloads,
            SaveDestination.NEXT_TO_SOURCE: self._radio_next,
            SaveDestination.ALWAYS_ASK: self._radio_ask,
            SaveDestination.CUSTOM: self._radio_custom,
        }.get(dest, self._radio_downloads).setChecked(True)

        # Theme
        theme_box = QGroupBox("FileForge appearance")
        theme_layout = QVBoxLayout(theme_box)
        self._theme_group = QButtonGroup(self)
        self._radio_forge = QRadioButton("Forge (dark, warm ember tones)")
        self._radio_daylight = QRadioButton("Daylight smithy (light mode)")
        self._theme_group.addButton(self._radio_forge, 0)
        self._theme_group.addButton(self._radio_daylight, 1)
        theme_layout.addWidget(self._radio_forge)
        theme_layout.addWidget(self._radio_daylight)
        if self._settings.theme == ThemeMode.DAYLIGHT.value:
            self._radio_daylight.setChecked(True)
        else:
            self._radio_forge.setChecked(True)
        root.addWidget(theme_box)

        hint = QLabel(
            "Converted files stay in a private cache until you click Download. "
            "Staging is cleared on exit; leftovers older than 24h are purged on startup."
        )
        hint.setObjectName("subtitleLabel")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_custom(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Custom save folder")
        if path:
            self._custom_edit.setText(path)
            self._radio_custom.setChecked(True)

    def result_settings(self) -> AppSettings:
        if self._radio_next.isChecked():
            dest = SaveDestination.NEXT_TO_SOURCE.value
        elif self._radio_ask.isChecked():
            dest = SaveDestination.ALWAYS_ASK.value
        elif self._radio_custom.isChecked():
            dest = SaveDestination.CUSTOM.value
        else:
            dest = SaveDestination.DOWNLOADS.value

        theme = (
            ThemeMode.DAYLIGHT.value
            if self._radio_daylight.isChecked()
            else ThemeMode.FORGE.value
        )
        return AppSettings(
            save_destination=dest,
            custom_save_dir=self._custom_edit.text().strip(),
            theme=theme,
            warn_large_files=self._settings.warn_large_files,
            large_file_threshold_mb=self._settings.large_file_threshold_mb,
        )
