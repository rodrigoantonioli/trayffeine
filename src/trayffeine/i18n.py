from __future__ import annotations

import locale
import sys
from dataclasses import dataclass
from typing import Literal

LocaleCode = Literal["en", "pt-BR", "es"]

SUPPORTED_LOCALES: tuple[LocaleCode, ...] = ("en", "pt-BR", "es")
FALLBACK_LOCALE: LocaleCode = "en"

Catalog = dict[str, str]

CATALOGS: dict[LocaleCode, Catalog] = {
    "en": {
        "app.name": "Trayffeine",
        "tray.tooltip.active_infinite": "Trayffeine: active (infinite)",
        "tray.tooltip.active_remaining": "Trayffeine: active ({remaining} left)",
        "tray.tooltip.inactive": "Trayffeine: inactive",
        "tray.menu.off": "Turn off",
        "tray.menu.quit": "Quit",
        "tray.menu.language": "Language",
        "tray.menu.language.auto": "Auto",
        "tray.notify.timer_finished.title": "Trayffeine",
        "tray.notify.timer_finished.body": "Session ended. Trayffeine returned to inactive mode.",
        "preset.15m": "15 min",
        "preset.30m": "30 min",
        "preset.1h": "1 h",
        "preset.2h": "2 h",
        "preset.infinite": "Infinite",
        "duration.hours_minutes": "{hours}h {minutes:02d}m",
        "duration.minutes_seconds": "{minutes}m {seconds:02d}s",
        "duration.seconds": "{seconds}s",
    },
    "pt-BR": {
        "app.name": "Trayffeine",
        "tray.tooltip.active_infinite": "Trayffeine: ativo (infinito)",
        "tray.tooltip.active_remaining": "Trayffeine: ativo ({remaining} restantes)",
        "tray.tooltip.inactive": "Trayffeine: inativo",
        "tray.menu.off": "Desligar",
        "tray.menu.quit": "Sair",
        "tray.menu.language": "Idioma",
        "tray.menu.language.auto": "Auto",
        "tray.notify.timer_finished.title": "Trayffeine",
        "tray.notify.timer_finished.body": "Sessão encerrada. O Trayffeine voltou ao modo inativo.",
        "preset.15m": "15 min",
        "preset.30m": "30 min",
        "preset.1h": "1 h",
        "preset.2h": "2 h",
        "preset.infinite": "Infinito",
        "duration.hours_minutes": "{hours}h {minutes:02d}m",
        "duration.minutes_seconds": "{minutes}m {seconds:02d}s",
        "duration.seconds": "{seconds}s",
    },
    "es": {
        "app.name": "Trayffeine",
        "tray.tooltip.active_infinite": "Trayffeine: activo (infinito)",
        "tray.tooltip.active_remaining": "Trayffeine: activo ({remaining} restantes)",
        "tray.tooltip.inactive": "Trayffeine: inactivo",
        "tray.menu.off": "Desactivar",
        "tray.menu.quit": "Salir",
        "tray.menu.language": "Idioma",
        "tray.menu.language.auto": "Auto",
        "tray.notify.timer_finished.title": "Trayffeine",
        "tray.notify.timer_finished.body": "La sesión terminó. Trayffeine volvió al modo inactivo.",
        "preset.15m": "15 min",
        "preset.30m": "30 min",
        "preset.1h": "1 h",
        "preset.2h": "2 h",
        "preset.infinite": "Infinito",
        "duration.hours_minutes": "{hours}h {minutes:02d}m",
        "duration.minutes_seconds": "{minutes}m {seconds:02d}s",
        "duration.seconds": "{seconds}s",
    },
}

NATIVE_LANGUAGE_NAMES: dict[LocaleCode, str] = {
    "en": "English",
    "pt-BR": "Português (Brasil)",
    "es": "Español",
}


@dataclass(frozen=True)
class LanguageSelection:
    mode: Literal["auto", "manual"]
    locale: LocaleCode | None = None

    @classmethod
    def auto(cls) -> LanguageSelection:
        return cls(mode="auto")

    @classmethod
    def explicit(cls, locale_code: LocaleCode) -> LanguageSelection:
        return cls(mode="manual", locale=locale_code)


@dataclass(frozen=True)
class LanguageOption:
    key: str
    label: str
    checked: bool


class Translator:
    def __init__(
        self,
        locale_code: LocaleCode,
        fallback_locale: LocaleCode = FALLBACK_LOCALE,
    ) -> None:
        self.locale = locale_code
        self.fallback_locale = fallback_locale

    def t(self, message_id: str, **params: object) -> str:
        message = CATALOGS[self.locale].get(message_id)
        if message is None:
            message = CATALOGS[self.fallback_locale].get(message_id, message_id)
        return message.format(**params)


def resolve_system_locale(raw_locale: str | None) -> LocaleCode:
    if raw_locale is None:
        return FALLBACK_LOCALE

    normalized = raw_locale.replace("_", "-").lower()
    if normalized.startswith("pt"):
        return "pt-BR"
    if normalized.startswith("es"):
        return "es"
    if normalized.startswith("en"):
        return "en"
    return FALLBACK_LOCALE


def detect_system_locale() -> LocaleCode:
    return resolve_system_locale(_raw_system_locale())


def effective_locale(selection: LanguageSelection, system_locale: LocaleCode) -> LocaleCode:
    if selection.mode == "manual" and selection.locale is not None:
        return selection.locale
    return system_locale


def build_language_options(
    selection: LanguageSelection,
    system_locale: LocaleCode,
    translator: Translator,
) -> tuple[LanguageOption, ...]:
    return (
        LanguageOption(
            key="auto",
            label=translator.t("tray.menu.language.auto"),
            checked=selection.mode == "auto",
        ),
        *(
            LanguageOption(
                key=locale_code,
                label=NATIVE_LANGUAGE_NAMES[locale_code],
                checked=selection.mode == "manual" and selection.locale == locale_code,
            )
            for locale_code in SUPPORTED_LOCALES
        ),
    )


def _raw_system_locale() -> str | None:
    if sys.platform == "win32":
        windows_locale = _windows_locale_name()
        if windows_locale is not None:
            return windows_locale

    current_locale = locale.getlocale()[0]
    if current_locale is not None:
        return current_locale

    return locale.getdefaultlocale()[0]


def _windows_locale_name() -> str | None:
    if sys.platform != "win32":
        return None

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    buffer = ctypes.create_unicode_buffer(85)
    result = kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
    if result <= 0:
        return None
    return buffer.value
