from __future__ import annotations

import ntpath
import os
from dataclasses import dataclass

from .keepawake import KeepAwakeMethod


@dataclass(frozen=True)
class DiagnosticsInfo:
    version: str
    language_selection: str
    effective_locale: str
    session_state: str
    configured_keepawake_method: KeepAwakeMethod
    effective_keepawake_method: KeepAwakeMethod | None
    presence_compatibility_enabled: bool
    detailed_logging_enabled: bool
    start_with_windows: bool
    settings_path: str
    log_path: str


def build_diagnostics_text(info: DiagnosticsInfo) -> str:
    effective_method = info.effective_keepawake_method or info.configured_keepawake_method
    return "\n".join(
        [
            "Trayffeine diagnostics",
            f"Version: {info.version}",
            f"Language selection: {info.language_selection}",
            f"Effective locale: {info.effective_locale}",
            f"Session state: {info.session_state}",
            f"Configured keep-awake method: {info.configured_keepawake_method}",
            f"Effective keep-awake method: {effective_method}",
            f"Presence compatibility: {_enabled_text(info.presence_compatibility_enabled)}",
            f"Detailed logging: {_enabled_text(info.detailed_logging_enabled)}",
            f"Start with Windows: {_enabled_text(info.start_with_windows)}",
            f"Settings path: {_privacy_safe_path(info.settings_path)}",
            f"Log path: {_privacy_safe_path(info.log_path)}",
        ]
    )


def _enabled_text(enabled: bool) -> str:
    return "enabled" if enabled else "disabled"


def _privacy_safe_path(path: str) -> str:
    normalized_path = path.replace("/", "\\")
    for variable_name in ("LOCALAPPDATA", "USERPROFILE"):
        raw_prefix = os.environ.get(variable_name)
        if not raw_prefix:
            continue

        normalized_prefix = raw_prefix.replace("/", "\\").rstrip("\\")
        comparable_path = ntpath.normcase(normalized_path)
        comparable_prefix = ntpath.normcase(normalized_prefix)
        if comparable_path == comparable_prefix:
            return f"%{variable_name}%"
        if comparable_path.startswith(f"{comparable_prefix}\\"):
            suffix = normalized_path[len(normalized_prefix) :]
            return f"%{variable_name}%{suffix}"

    return path
