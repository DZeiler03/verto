#!/usr/bin/env python3
"""Verto — offline desktop file converter.

Entry point. Morphix performs all conversion work; the UI is FileForge-themed
(full anvil/hammer experience lands in Phase 3).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python src/main.py` and `PYTHONPATH=src python -m main`
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    from utils.logging_setup import setup_logging

    logger = setup_logging()
    logger.info("Starting Verto")

    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Verto")
    app.setOrganizationName("Verto")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
