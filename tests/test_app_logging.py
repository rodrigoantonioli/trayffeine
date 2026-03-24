from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from trayffeine.app_logging import (
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_MAX_BYTES,
    clear_log_files,
    configure_logging,
    effective_log_level,
    is_detailed_logging_level,
    is_log_level_locked_by_env,
    set_runtime_log_level,
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


def test_effective_log_level_uses_env_override(monkeypatch) -> None:
    monkeypatch.setenv("TRAYFFEINE_LOG_LEVEL", "INFO")

    assert effective_log_level(False) == logging.INFO
    assert is_log_level_locked_by_env() is True
    assert is_detailed_logging_level(logging.INFO) is True


def test_set_runtime_log_level_reuses_existing_handler(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers = []

    try:
        configure_logging(level=logging.WARNING)
        first_handler = root.handlers[0]

        set_runtime_log_level(logging.INFO)

        assert len(root.handlers) == 1
        assert root.handlers[0] is first_handler
        assert root.level == logging.INFO
        assert root.handlers[0].level == logging.INFO
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers = previous_handlers
        root.setLevel(previous_level)


def test_clear_log_files_removes_current_and_rotated_logs(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers = []

    try:
        log_path = configure_logging(level=logging.INFO)
        logger = logging.getLogger("trayffeine.tests")
        logger.info("hello")
        for handler in root.handlers:
            handler.flush()
        log_path.with_suffix(".log.1").write_text("backup", encoding="utf-8")

        clear_log_files(log_path)

        assert not log_path.exists()
        assert not log_path.with_suffix(".log.1").exists()
        assert root.handlers == []
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers = previous_handlers
        root.setLevel(previous_level)
