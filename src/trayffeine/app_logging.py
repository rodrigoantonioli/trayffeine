from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_MAX_BYTES = 256 * 1024
DEFAULT_LOG_BACKUP_COUNT = 3


def configure_logging() -> Path:
    log_path = default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    log_level = configured_log_level()
    root.setLevel(log_level)

    existing_handler = next(
        (
            handler
            for handler in root.handlers
            if isinstance(handler, logging.FileHandler)
            and Path(handler.baseFilename) == log_path
        ),
        None,
    )
    if existing_handler is not None:
        existing_handler.setLevel(log_level)
        return log_path

    handler = RotatingFileHandler(
        log_path,
        encoding="utf-8",
        maxBytes=DEFAULT_LOG_MAX_BYTES,
        backupCount=DEFAULT_LOG_BACKUP_COUNT,
    )
    handler.setLevel(log_level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    return log_path


def configured_log_level() -> int:
    level_name = os.environ.get("TRAYFFEINE_LOG_LEVEL", "WARNING").upper()
    return getattr(logging, level_name, logging.WARNING)


def default_log_path() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Trayffeine" / "logs" / "trayffeine.log"
    return Path.home() / "AppData" / "Local" / "Trayffeine" / "logs" / "trayffeine.log"
