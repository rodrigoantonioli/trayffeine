from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trayffeine.presenter import build_menu_entries, icon_variant, tooltip_text
from trayffeine.session import SessionMode


def test_inactive_state_has_inactive_icon_and_disabled_off() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)

    entries = build_menu_entries(SessionMode.off(), now)

    assert icon_variant(SessionMode.off(), now) == "inactive"
    assert tooltip_text(SessionMode.off(), now) == "Trayffeine: inativo"
    assert next(entry for entry in entries if entry.key == "off").enabled is False
    assert all(entry.checked is False for entry in entries if entry.key not in {"off", "quit"})


def test_timed_state_marks_the_selected_preset() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    mode = SessionMode.timed(now + timedelta(minutes=15), preset_key="15m")

    entries = build_menu_entries(mode, now)

    assert icon_variant(mode, now) == "active"
    assert tooltip_text(mode, now).startswith("Trayffeine: ativo")
    assert next(entry for entry in entries if entry.key == "15m").checked is True
    assert next(entry for entry in entries if entry.key == "off").enabled is True


def test_infinite_state_marks_infinite_preset() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    entries = build_menu_entries(SessionMode.infinite(), now)

    assert next(entry for entry in entries if entry.key == "infinite").checked is True

