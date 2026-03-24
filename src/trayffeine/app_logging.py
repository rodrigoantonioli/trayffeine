from __future__ import annotations

import logging
import os
from pathlib import Path


def configure_logging() -> Path:
    log_path = default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_path
        for handler in root.handlers
    ):
        return log_path

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return log_path


def default_log_path() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Trayffeine" / "logs" / "trayffeine.log"
    return Path.home() / "AppData" / "Local" / "Trayffeine" / "logs" / "trayffeine.log"
