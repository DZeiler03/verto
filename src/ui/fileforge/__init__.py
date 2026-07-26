"""FileForge — Verto's blacksmith-forge visual theme.

The entire UI is themed as a blacksmith's forge: anvil input slot, hammer-strike
animation synced to Morphix jobs, output slot for forged results, and an
inventory-style forge queue. Cosmetic sugar only — status and errors stay visible.
"""

from ui.fileforge.anvil import AnvilWidget
from ui.fileforge.hammer import HammerOverlay
from ui.fileforge.output_slot import OutputSlot
from ui.fileforge.queue_row import ForgeQueueRow
from ui.fileforge.theme import (
    COAL,
    DAYLIGHT_BG,
    DAYLIGHT_FG,
    EMBER,
    IRON,
    SPARK,
    STEEL,
    ThemeMode,
    stylesheet,
)

__all__ = [
    "AnvilWidget",
    "HammerOverlay",
    "OutputSlot",
    "ForgeQueueRow",
    "ThemeMode",
    "stylesheet",
    "EMBER",
    "COAL",
    "STEEL",
    "SPARK",
    "IRON",
    "DAYLIGHT_BG",
    "DAYLIGHT_FG",
]
