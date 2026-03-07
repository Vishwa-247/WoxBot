"""
WoxBot Logging Module
Provides a pre-configured logger for the entire application.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.core.config import get_settings, BASE_DIR


def setup_logger(name: str = "woxbot") -> logging.Logger:
    """Create and configure the application logger.

    - Logs to stdout (for container / dev friendliness)
    - Logs to file  logs/woxbot.log  (rolling reference)
    """
    settings = get_settings()

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.DEBUG))

    # Prevent duplicate handlers on re-import
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler ──────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # ── File handler ─────────────────────────────────────
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "woxbot.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Module-level logger ready to import anywhere:
#   from app.core.logger import logger
logger = setup_logger()
