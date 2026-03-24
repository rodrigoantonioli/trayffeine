from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from .i18n import FALLBACK_LOCALE, SUPPORTED_LOCALES, LanguageSelection, LocaleCode

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredSettings:
    language_selection: LanguageSelection
    restore_infinite: bool = False
    detailed_logging_enabled: bool = False


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_settings_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> StoredSettings:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return StoredSettings(language_selection=LanguageSelection.auto())
        except (OSError, json.JSONDecodeError):
            LOGGER.exception("Failed to load settings from %s", self._path)
            return StoredSettings(language_selection=LanguageSelection.auto())
        return _deserialize_settings(data)

    def save(self, settings: StoredSettings) -> None:
        payload = _serialize_settings(settings)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            LOGGER.exception("Failed to save settings to %s", self._path)


def default_settings_path() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Trayffeine" / "settings.json"
    return Path.home() / "AppData" / "Local" / "Trayffeine" / "settings.json"


def _serialize_settings(settings: StoredSettings) -> dict[str, object]:
    return {
        "language_selection": {
            "mode": settings.language_selection.mode,
            "locale": settings.language_selection.locale,
        },
        "restore_infinite": settings.restore_infinite,
        "detailed_logging_enabled": settings.detailed_logging_enabled,
    }


def _deserialize_settings(payload: object) -> StoredSettings:
    if not isinstance(payload, dict):
        return StoredSettings(language_selection=LanguageSelection.auto())

    restore_infinite = bool(payload.get("restore_infinite", False))
    detailed_logging_enabled = bool(payload.get("detailed_logging_enabled", False))
    raw_language = payload.get("language_selection")
    language_selection = _deserialize_language_selection(raw_language)
    return StoredSettings(
        language_selection=language_selection,
        restore_infinite=restore_infinite,
        detailed_logging_enabled=detailed_logging_enabled,
    )


def _deserialize_language_selection(payload: object) -> LanguageSelection:
    if not isinstance(payload, dict):
        return LanguageSelection.auto()

    mode = payload.get("mode")
    locale = payload.get("locale")
    if mode == "manual" and locale in SUPPORTED_LOCALES:
        return LanguageSelection.explicit(locale)
    if mode == "manual" and isinstance(locale, str):
        return LanguageSelection.explicit(_coerce_locale(locale))
    return LanguageSelection.auto()


def _coerce_locale(locale: str) -> LocaleCode:
    normalized = locale.replace("_", "-").lower()
    for supported in SUPPORTED_LOCALES:
        if normalized == supported.lower():
            return supported
    return FALLBACK_LOCALE
