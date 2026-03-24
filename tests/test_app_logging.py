from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from trayffeine.app_logging import (
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_MAX_BYTES,
    configure_logging,
)


def test_configure_logging_uses_rotation_and_warning_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers = []

    try:
        log_path = configure_logging()

        handler = root.handlers[0]

        assert log_path == tmp_path / "Trayffeine" / "logs" / "trayffeine.log"
        assert isinstance(handler, RotatingFileHandler)
        assert handler.maxBytes == DEFAULT_LOG_MAX_BYTES
        assert handler.backupCount == DEFAULT_LOG_BACKUP_COUNT
        assert root.level == logging.WARNING
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers = previous_handlers
        root.setLevel(previous_level)


def test_configure_logging_respects_log_level_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("TRAYFFEINE_LOG_LEVEL", "INFO")
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers = []

    try:
        configure_logging()

        assert root.level == logging.INFO
        assert root.handlers[0].level == logging.INFO
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers = previous_handlers
        root.setLevel(previous_level)
