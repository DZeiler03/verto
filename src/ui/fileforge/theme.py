"""FileForge visual theme — palettes, stylesheets, scene colors.

Supports dark *Forge* and light *Daylight smithy* modes. Custom-painted widgets
use :func:`palette_for` so glows and metals track the active theme.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThemeMode(str, Enum):
    FORGE = "forge"
    DAYLIGHT = "daylight"


# Legacy string constants (QSS + backwards compat)
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


@dataclass(frozen=True)
class ScenePalette:
    """Colors for custom-painted FileForge scene widgets."""

    # Room
    bg: str
    bg_mid: str
    floor: str
    wall: str
    # Metal
    metal_dark: str
    metal_mid: str
    metal_light: str
    metal_edge: str
    # Warm light / fire
    glow: str
    glow_soft: str
    flame_core: str
    flame_mid: str
    flame_edge: str
    ember: str
    # UI paint
    text: str
    text_dim: str
    ash: str
    slot_fill: str
    panel: str
    wood: str
    stone: str
    success: str
    error: str
    accent: str


def _norm_mode(mode: ThemeMode | str) -> ThemeMode:
    if isinstance(mode, ThemeMode):
        return mode
    try:
        return ThemeMode(str(mode))
    except ValueError:
        return ThemeMode.FORGE


def palette_for(mode: ThemeMode | str) -> ScenePalette:
    """Return the scene paint palette for the given theme mode."""
    mode = _norm_mode(mode)
    if mode == ThemeMode.DAYLIGHT:
        return ScenePalette(
            bg=DAYLIGHT_BG,
            bg_mid="#EDE4D4",
            floor="#D4C4A8",
            wall="#E8DFD0",
            metal_dark="#4A4A52",
            metal_mid="#7A7A85",
            metal_light="#B0B0BB",
            metal_edge="#2A2A30",
            glow="#E85D04",
            glow_soft="#F4A261",
            flame_core="#FFE566",
            flame_mid="#F48C06",
            flame_edge="#E85D04",
            ember="#FFBA08",
            text=DAYLIGHT_FG,
            text_dim="#5A5348",
            ash="#8A8070",
            slot_fill="#00000028",
            panel=DAYLIGHT_PANEL,
            wood="#A67C52",
            stone="#C4B8A8",
            success=SUCCESS,
            error=ERROR,
            accent=EMBER,
        )
    # Dark forge
    return ScenePalette(
        bg=COAL,
        bg_mid="#1A1410",
        floor="#0E0C0A",
        wall="#181410",
        metal_dark="#1A1A1C",
        metal_mid="#3A3A42",
        metal_light="#8A8A95",
        metal_edge="#0A0A0C",
        glow=EMBER_GLOW,
        glow_soft="#E85D0480",
        flame_core="#FFF3A0",
        flame_mid="#FF9F1C",
        flame_edge="#E85D04",
        ember=SPARK,
        text="#F0E6D8",
        text_dim=ASH,
        ash=ASH,
        slot_fill="#00000066",
        panel=IRON,
        wood="#5D4037",
        stone="#2B2520",
        success=SUCCESS,
        error=ERROR,
        accent=EMBER,
    )


def stylesheet(mode: ThemeMode | str) -> str:
    mode = _norm_mode(mode)
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
    QWidget#forgeScene {{
        background: transparent;
        border: 1px solid #2A2218;
        border-radius: 10px;
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
        border-radius: 6px;
        padding: 6px 10px;
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: {SPARK};
        background-color: #282828;
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
        background-color: #353535;
        color: #F0E6D8;
        border: 1px solid #5A5A5A;
        border-radius: 6px;
        padding: 8px 14px;
    }}
    QPushButton:hover {{
        background-color: #454545;
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
        border-radius: 8px;
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
        border-radius: 6px;
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
    QWidget#forgeScene {{
        background: transparent;
        border: 1px solid {DAYLIGHT_BORDER};
        border-radius: 10px;
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
        border-radius: 6px;
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
        border-radius: 6px;
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
        border-radius: 8px;
    }}
    QPushButton#forgeButton:hover {{
        background-color: {EMBER_GLOW};
    }}
    QPushButton#downloadButton {{
        background-color: {SUCCESS};
        color: white;
        border: 1px solid #388E3C;
        font-weight: bold;
        border-radius: 6px;
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
