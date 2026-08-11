"""FileForge — Verto's blacksmith-forge visual theme.

Atmospheric 2D smithy: forge oven with flame animation, metallic anvil, hammer
strike, output slot, and inventory-style queue. Cosmetic layer only — status
and errors stay clearly visible.
"""

from ui.fileforge.anvil import AnvilWidget
from ui.fileforge.hammer import HammerOverlay
from ui.fileforge.output_slot import OutputSlot
from ui.fileforge.oven import ForgeOvenWidget
from ui.fileforge.queue_row import ForgeQueueRow
from ui.fileforge.scene import ForgeSceneWidget
from ui.fileforge.theme import (
    COAL,
    DAYLIGHT_BG,
    DAYLIGHT_FG,
    EMBER,
    IRON,
    SPARK,
    STEEL,
    ScenePalette,
    ThemeMode,
    palette_for,
    stylesheet,
)

__all__ = [
    "AnvilWidget",
    "HammerOverlay",
    "OutputSlot",
    "ForgeOvenWidget",
    "ForgeQueueRow",
    "ForgeSceneWidget",
    "ThemeMode",
    "ScenePalette",
    "palette_for",
    "stylesheet",
    "EMBER",
    "COAL",
    "STEEL",
    "SPARK",
    "IRON",
    "DAYLIGHT_BG",
    "DAYLIGHT_FG",
]
