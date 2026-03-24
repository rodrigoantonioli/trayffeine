from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from . import __version__
from .i18n import LanguageSelection, Translator, build_language_options
from .keepawake import SUPPORTED_KEEPAWAKE_METHODS, KeepAwakeMethod
from .session import PRESETS, DurationPreset, SessionMode


@dataclass(frozen=True)
class MenuEntry:
    key: str
    text: str
    checked: bool = False
    enabled: bool = True


@dataclass(frozen=True)
class InfoEntry:
    key: str
    text: str


def app_name(translator: Translator) -> str:
    return translator.t("app.name")


def icon_variant(mode: SessionMode, now: datetime) -> str:
    return "active" if mode.is_active(now) else "inactive"


def build_status_entries(
    mode: SessionMode,
    now: datetime,
    translator: Translator,
) -> tuple[InfoEntry, ...]:
    return (
        InfoEntry(key="header", text=translator.t("tray.menu.header", version=__version__)),
        InfoEntry(key="summary", text=menu_summary_text(mode, now, translator)),
    )


def tooltip_text(mode: SessionMode, now: datetime, translator: Translator) -> str:
    if mode.kind == "infinite" and mode.is_active(now):
        elapsed = format_duration(mode.elapsed(now), translator)
        return translator.t("tray.tooltip.active_infinite", elapsed=elapsed)

    if mode.kind == "timed" and mode.ends_at is not None and mode.is_active(now):
        elapsed = format_duration(mode.elapsed(now), translator)
        remaining = format_duration(mode.remaining(now), translator)
        return translator.t(
            "tray.tooltip.active_remaining",
            elapsed=elapsed,
            remaining=remaining,
        )

    return translator.t("tray.tooltip.inactive")


def build_menu_entries(
    mode: SessionMode,
    now: datetime,
    translator: Translator,
) -> tuple[MenuEntry, ...]:
    return (
        MenuEntry(
            key="infinite",
            text=translator.t("tray.menu.infinite"),
            checked=mode.kind == "infinite" and mode.is_active(now),
            enabled=not (mode.kind == "infinite" and mode.is_active(now)),
        ),
        MenuEntry(key="stop", text=translator.t("tray.menu.stop"), enabled=mode.is_active(now)),
        MenuEntry(key="quit", text=translator.t("tray.menu.quit")),
    )


def build_duration_menu_entries(
    mode: SessionMode,
    now: datetime,
    translator: Translator,
) -> tuple[MenuEntry, ...]:
    return tuple(
        _preset_entry(mode, now, preset, translator)
        for preset in PRESETS
        if preset.key != "infinite"
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


def build_keepawake_method_menu_entries(
    selected_method: KeepAwakeMethod,
    translator: Translator,
) -> tuple[MenuEntry, ...]:
    return tuple(
        MenuEntry(
            key=method,
            text=translator.t(f"tray.keepawake_method.{method}"),
            checked=selected_method == method,
        )
        for method in SUPPORTED_KEEPAWAKE_METHODS
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


def remaining_text(mode: SessionMode, now: datetime, translator: Translator) -> str:
    if mode.kind == "infinite" and mode.is_active(now):
        return translator.t("tray.status.infinite")
    if mode.kind == "timed" and mode.ends_at is not None and mode.is_active(now):
        return format_duration(mode.remaining(now), translator)
    return translator.t("tray.status.none")


def menu_summary_text(mode: SessionMode, now: datetime, translator: Translator) -> str:
    if mode.kind == "infinite" and mode.is_active(now):
        return translator.t("tray.summary.infinite")
    if mode.kind == "timed" and mode.ends_at is not None and mode.is_active(now):
        return translator.t("tray.summary.timed", time=format_clock(mode.ends_at))
    return translator.t("tray.summary.inactive")


def format_duration(delta: timedelta, translator: Translator) -> str:
    total_seconds = max(0, int(delta.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return translator.t("duration.hours_minutes", hours=hours, minutes=minutes)
    if minutes:
        return translator.t("duration.minutes_seconds", minutes=minutes, seconds=seconds)
    return translator.t("duration.seconds", seconds=seconds)


def format_clock(moment: datetime) -> str:
    return moment.astimezone().strftime("%H:%M")
