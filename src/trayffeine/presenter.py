from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .session import PRESETS, DurationPreset, SessionMode


@dataclass(frozen=True)
class MenuEntry:
    key: str
    text: str
    checked: bool = False
    enabled: bool = True


def icon_variant(mode: SessionMode, now: datetime) -> str:
    return "active" if mode.is_active(now) else "inactive"


def tooltip_text(mode: SessionMode, now: datetime) -> str:
    if mode.kind == "infinite":
        return "Trayffeine: ativo (infinito)"

    if mode.kind == "timed" and mode.ends_at is not None and mode.is_active(now):
        remaining = format_remaining(mode.remaining(now))
        return f"Trayffeine: ativo ({remaining} restantes)"

    return "Trayffeine: inativo"


def build_menu_entries(mode: SessionMode, now: datetime) -> tuple[MenuEntry, ...]:
    preset_entries = tuple(_preset_entry(mode, now, preset) for preset in PRESETS)
    return (
        *preset_entries,
        MenuEntry(key="off", text="Desligar", enabled=mode.is_active(now)),
        MenuEntry(key="quit", text="Sair"),
    )


def _preset_entry(mode: SessionMode, now: datetime, preset: DurationPreset) -> MenuEntry:
    checked = mode.is_active(now) and mode.preset_key == preset.key
    return MenuEntry(key=preset.key, text=preset.label, checked=checked)


def format_remaining(delta: timedelta) -> str:
    total_seconds = max(0, int(delta.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"

