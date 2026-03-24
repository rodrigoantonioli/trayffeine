from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .i18n import LanguageSelection, Translator, build_language_options
from .session import PRESETS, DurationPreset, SessionMode


@dataclass(frozen=True)
class MenuEntry:
    key: str
    text: str
    checked: bool = False
    enabled: bool = True


def app_name(translator: Translator) -> str:
    return translator.t("app.name")


def icon_variant(mode: SessionMode, now: datetime) -> str:
    return "active" if mode.is_active(now) else "inactive"


def tooltip_text(mode: SessionMode, now: datetime, translator: Translator) -> str:
    if mode.kind == "infinite":
        return translator.t("tray.tooltip.active_infinite")

    if mode.kind == "timed" and mode.ends_at is not None and mode.is_active(now):
        remaining = format_remaining(mode.remaining(now), translator)
        return translator.t("tray.tooltip.active_remaining", remaining=remaining)

    return translator.t("tray.tooltip.inactive")


def build_menu_entries(
    mode: SessionMode,
    now: datetime,
    translator: Translator,
) -> tuple[MenuEntry, ...]:
    preset_entries = tuple(_preset_entry(mode, now, preset, translator) for preset in PRESETS)
    return (
        *preset_entries,
        MenuEntry(key="off", text=translator.t("tray.menu.off"), enabled=mode.is_active(now)),
        MenuEntry(key="quit", text=translator.t("tray.menu.quit")),
    )


def build_language_menu_entries(
    selection: LanguageSelection,
    system_locale: str,
    translator: Translator,
) -> tuple[MenuEntry, ...]:
    return tuple(
        MenuEntry(key=option.key, text=option.label, checked=option.checked)
        for option in build_language_options(selection, system_locale, translator)
    )


def timer_finished_notification(translator: Translator) -> tuple[str, str]:
    return (
        translator.t("tray.notify.timer_finished.title"),
        translator.t("tray.notify.timer_finished.body"),
    )


def _preset_entry(
    mode: SessionMode,
    now: datetime,
    preset: DurationPreset,
    translator: Translator,
) -> MenuEntry:
    checked = mode.is_active(now) and mode.preset_key == preset.key
    return MenuEntry(key=preset.key, text=translator.t(f"preset.{preset.key}"), checked=checked)


def format_remaining(delta: timedelta, translator: Translator) -> str:
    total_seconds = max(0, int(delta.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return translator.t("duration.hours_minutes", hours=hours, minutes=minutes)
    if minutes:
        return translator.t("duration.minutes_seconds", minutes=minutes, seconds=seconds)
    return translator.t("duration.seconds", seconds=seconds)
