"""FileForge visual theme — forge (dark) and daylight (light) stylesheets."""

from __future__ import annotations

from enum import Enum


class ThemeMode(str, Enum):
    FORGE = "forge"
    DAYLIGHT = "daylight"


# Palette
EMBER = "#E85D04"
EMBER_GLOW = "#F48C06"
COAL = "#121212"
IRON = "#1E1E1E"
STEEL = "#3A3A3A"
ASH = "#8A8A8A"
SPARK = "#FFBA08"
ANVIL = "#2C2C2C"
HAMMER = "#C0C0C0"
SUCCESS = "#4CAF50"
ERROR = "#D32F2F"
DAYLIGHT_BG = "#F5F0E8"
DAYLIGHT_FG = "#1A1A1A"
DAYLIGHT_PANEL = "#FFFCF7"
DAYLIGHT_BORDER = "#C4B8A8"


def stylesheet(mode: ThemeMode | str) -> str:
    mode = ThemeMode(mode) if not isinstance(mode, ThemeMode) else mode
    if mode == ThemeMode.DAYLIGHT:
        return _daylight_qss()
    return _forge_qss()


def _forge_qss() -> str:
    return f"""
    QMainWindow, QDialog {{
        background-color: {COAL};
        color: #F0E6D8;
    }}
    QWidget#centralRoot {{
        background-color: {COAL};
        color: #F0E6D8;
    }}
    QLabel {{
        color: #F0E6D8;
        background: transparent;
    }}
    QLabel#titleLabel {{
        font-size: 24px;
        font-weight: bold;
        color: {EMBER_GLOW};
    }}
    QLabel#subtitleLabel {{
        font-size: 12px;
        color: {ASH};
    }}
    QLabel#statusDetail {{
        font-size: 12px;
        color: {SPARK};
    }}
    QComboBox {{
        background-color: {IRON};
        color: #F0E6D8;
        border: 1px solid {EMBER};
        border-radius: 4px;
        padding: 6px 10px;
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: {SPARK};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {IRON};
        color: #F0E6D8;
        selection-background-color: {EMBER};
        border: 1px solid {STEEL};
    }}
    QPushButton {{
        background-color: {STEEL};
        color: #F0E6D8;
        border: 1px solid {ASH};
        border-radius: 4px;
        padding: 8px 14px;
    }}
    QPushButton:hover {{
        background-color: #4A4A4A;
        border-color: {EMBER};
    }}
    QPushButton:disabled {{
        background-color: #2A2A2A;
        color: #666;
        border-color: #333;
    }}
    QPushButton#forgeButton {{
        background-color: {EMBER};
        color: white;
        font-weight: bold;
        font-size: 14px;
        border: 1px solid {EMBER_GLOW};
        padding: 10px 20px;
        border-radius: 6px;
    }}
    QPushButton#forgeButton:hover {{
        background-color: {EMBER_GLOW};
    }}
    QPushButton#forgeButton:disabled {{
        background-color: #5A3A20;
        color: #999;
    }}
    QPushButton#downloadButton {{
        background-color: #2E5A2E;
        color: white;
        border: 1px solid {SUCCESS};
        font-weight: bold;
    }}
    QPushButton#downloadButton:hover {{
        background-color: #3A7A3A;
    }}
    QPushButton#downloadButton:disabled {{
        background-color: #2A2A2A;
        color: #666;
        border-color: #333;
    }}
    QStatusBar {{
        background-color: {IRON};
        color: {ASH};
        border-top: 1px solid {STEEL};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QMessageBox {{
        background-color: {IRON};
        color: #F0E6D8;
    }}
    QLineEdit {{
        background-color: {ANVIL};
        color: #F0E6D8;
        border: 1px solid {STEEL};
        border-radius: 4px;
        padding: 6px;
    }}
    QGroupBox {{
        color: #F0E6D8;
        border: 1px solid {STEEL};
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 12px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {EMBER_GLOW};
    }}
    QRadioButton, QCheckBox {{
        color: #F0E6D8;
        spacing: 8px;
    }}
    QListWidget {{
        background-color: {IRON};
        color: #F0E6D8;
        border: 1px solid {STEEL};
        border-radius: 4px;
    }}
    """


def _daylight_qss() -> str:
    return f"""
    QMainWindow, QDialog {{
        background-color: {DAYLIGHT_BG};
        color: {DAYLIGHT_FG};
    }}
    QWidget#centralRoot {{
        background-color: {DAYLIGHT_BG};
        color: {DAYLIGHT_FG};
    }}
    QLabel {{
        color: {DAYLIGHT_FG};
        background: transparent;
    }}
    QLabel#titleLabel {{
        font-size: 24px;
        font-weight: bold;
        color: {EMBER};
    }}
    QLabel#subtitleLabel {{
        font-size: 12px;
        color: #666;
    }}
    QLabel#statusDetail {{
        font-size: 12px;
        color: #8B5A00;
    }}
    QComboBox {{
        background-color: {DAYLIGHT_PANEL};
        color: {DAYLIGHT_FG};
        border: 1px solid {DAYLIGHT_BORDER};
        border-radius: 4px;
        padding: 6px 10px;
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: {EMBER};
    }}
    QComboBox QAbstractItemView {{
        background-color: white;
        color: {DAYLIGHT_FG};
        selection-background-color: {EMBER};
        selection-color: white;
    }}
    QPushButton {{
        background-color: {DAYLIGHT_PANEL};
        color: {DAYLIGHT_FG};
        border: 1px solid {DAYLIGHT_BORDER};
        border-radius: 4px;
        padding: 8px 14px;
    }}
    QPushButton:hover {{
        border-color: {EMBER};
        background-color: #FFF5EB;
    }}
    QPushButton:disabled {{
        color: #999;
        background-color: #EEE;
    }}
    QPushButton#forgeButton {{
        background-color: {EMBER};
        color: white;
        font-weight: bold;
        font-size: 14px;
        border: 1px solid {EMBER};
        padding: 10px 20px;
        border-radius: 6px;
    }}
    QPushButton#forgeButton:hover {{
        background-color: {EMBER_GLOW};
    }}
    QPushButton#downloadButton {{
        background-color: {SUCCESS};
        color: white;
        border: 1px solid #388E3C;
        font-weight: bold;
    }}
    QPushButton#downloadButton:disabled {{
        background-color: #CCC;
        color: #888;
        border-color: #BBB;
    }}
    QStatusBar {{
        background-color: {DAYLIGHT_PANEL};
        color: #555;
        border-top: 1px solid {DAYLIGHT_BORDER};
    }}
    QGroupBox {{
        color: {DAYLIGHT_FG};
        border: 1px solid {DAYLIGHT_BORDER};
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 12px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {EMBER};
    }}
    QLineEdit {{
        background-color: white;
        color: {DAYLIGHT_FG};
        border: 1px solid {DAYLIGHT_BORDER};
        border-radius: 4px;
        padding: 6px;
    }}
    QListWidget {{
        background-color: white;
        color: {DAYLIGHT_FG};
        border: 1px solid {DAYLIGHT_BORDER};
        border-radius: 4px;
    }}
    """
