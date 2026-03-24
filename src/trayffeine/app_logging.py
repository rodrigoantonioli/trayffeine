from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_MAX_BYTES = 256 * 1024
DEFAULT_LOG_BACKUP_COUNT = 3
DEFAULT_LOG_LEVEL = logging.WARNING
DETAILED_LOG_LEVEL = logging.INFO
LOG_LEVEL_ENV_VAR = "TRAYFFEINE_LOG_LEVEL"
_LOG_HANDLER_NAME = "trayffeine-file-handler"
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(*, level: int | None = None, log_path: Path | None = None) -> Path:
    target_path = log_path or default_log_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    target_level = configured_log_level() if level is None else level
    root.setLevel(target_level)

    existing_handler = _managed_file_handler(root, target_path)
    if existing_handler is not None:
        existing_handler.setLevel(target_level)
        existing_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        return target_path

    handler = RotatingFileHandler(
        target_path,
        encoding="utf-8",
        maxBytes=DEFAULT_LOG_MAX_BYTES,
        backupCount=DEFAULT_LOG_BACKUP_COUNT,
    )
    handler.name = _LOG_HANDLER_NAME
    handler.setLevel(target_level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    return target_path


def configured_log_level() -> int:
    override = env_log_level_override()
    if override is not None:
        return override
    return DEFAULT_LOG_LEVEL


def env_log_level_override() -> int | None:
    raw_level = os.environ.get(LOG_LEVEL_ENV_VAR)
    if raw_level is None or raw_level.strip() == "":
        return None
    return getattr(logging, raw_level.upper(), DEFAULT_LOG_LEVEL)


def is_log_level_locked_by_env() -> bool:
    return env_log_level_override() is not None


def log_level_for_detailed_logging(enabled: bool) -> int:
    return DETAILED_LOG_LEVEL if enabled else DEFAULT_LOG_LEVEL


def effective_log_level(detailed_logging_enabled: bool) -> int:
    override = env_log_level_override()
    if override is not None:
        return override
    return log_level_for_detailed_logging(detailed_logging_enabled)


def is_detailed_logging_level(level: int) -> bool:
    return level <= DETAILED_LOG_LEVEL


def set_runtime_log_level(level: int, *, log_path: Path | None = None) -> Path:
    return configure_logging(level=level, log_path=log_path)


def clear_log_files(log_path: Path | None = None) -> None:
    target_path = log_path or default_log_path()
    root = logging.getLogger()
    handler = _managed_file_handler(root, target_path)
    if handler is not None:
        root.removeHandler(handler)
        handler.flush()
        handler.close()

    for candidate in _log_file_candidates(target_path):
        try:
            candidate.unlink()
        except FileNotFoundError:
            continue


def default_log_path() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Trayffeine" / "logs" / "trayffeine.log"
    return Path.home() / "AppData" / "Local" / "Trayffeine" / "logs" / "trayffeine.log"


def _managed_file_handler(
    root: logging.Logger, log_path: Path
) -> RotatingFileHandler | None:
    for handler in root.handlers:
        if not isinstance(handler, RotatingFileHandler):
            continue
        if Path(handler.baseFilename) != log_path:
            continue
        if handler.name != _LOG_HANDLER_NAME:
            handler.name = _LOG_HANDLER_NAME
        return handler
    return None


def _log_file_candidates(log_path: Path) -> list[Path]:
    return sorted(log_path.parent.glob(f"{log_path.name}*"))
