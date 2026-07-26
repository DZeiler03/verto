"""Local-only logging setup for Verto (no external services)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.paths import logs_dir


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logger with console + rotating local file handler."""
    logger = logging.getLogger("verto")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_path: Path = logs_dir() / "verto.log"
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.debug("Logging initialized at %s", log_path)
    return logger
