from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trayffeine.i18n import LanguageSelection, Translator
from trayffeine.presenter import (
    build_language_menu_entries,
    build_menu_entries,
    build_status_entries,
    icon_variant,
    timer_finished_notification,
    tooltip_text,
)
from trayffeine.session import SessionMode


def test_inactive_state_has_inactive_icon_and_disabled_off() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    translator = Translator("pt-BR")

    entries = build_menu_entries(SessionMode.off(), now, translator)
    status_entries = build_status_entries(SessionMode.off(), now, translator)

    assert icon_variant(SessionMode.off(), now) == "inactive"
    assert tooltip_text(SessionMode.off(), now, translator) == "Trayffeine: inativo"
    assert [entry.text for entry in status_entries] == [
        "Trayffeine v0.3.0",
        "Tempo ativo: 0s",
        "Tempo restante: -",
    ]
    assert next(entry for entry in entries if entry.key == "off").enabled is False
    assert all(entry.checked is False for entry in entries if entry.key not in {"off", "quit"})


def test_timed_state_marks_the_selected_preset() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    mode = SessionMode.timed(now, now + timedelta(minutes=15), preset_key="15m")
    translator = Translator("en")

    entries = build_menu_entries(mode, now, translator)
    status_entries = build_status_entries(mode, now + timedelta(minutes=1), translator)

    assert icon_variant(mode, now) == "active"
    assert tooltip_text(mode, now, translator) == "Trayffeine: active (15m 00s left)"
    assert [entry.text for entry in status_entries] == [
        "Trayffeine v0.3.0",
        "Elapsed: 1m 00s",
        "Remaining: 14m 00s",
    ]
    assert next(entry for entry in entries if entry.key == "15m").checked is True
    assert next(entry for entry in entries if entry.key == "off").enabled is True
    assert next(entry for entry in entries if entry.key == "off").text == "Turn off"


def test_infinite_state_marks_infinite_preset() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    translator = Translator("es")
    mode = SessionMode.infinite(now)
    entries = build_menu_entries(mode, now, translator)
    status_entries = build_status_entries(mode, now + timedelta(seconds=5), translator)

    assert next(entry for entry in entries if entry.key == "infinite").checked is True
    assert next(entry for entry in entries if entry.key == "infinite").text == "Infinito"
    assert [entry.text for entry in status_entries] == [
        "Trayffeine v0.3.0",
        "Tiempo activo: 5s",
        "Tiempo restante: Infinito",
    ]
    assert timer_finished_notification(translator) == (
        "Trayffeine",
        "La sesión terminó. Trayffeine volvió al modo inactivo.",
    )


def test_language_menu_entries_reflect_auto_selection() -> None:
    entries = build_language_menu_entries(
        LanguageSelection.auto(),
        "pt-BR",
        Translator("pt-BR"),
    )

    assert [entry.text for entry in entries] == [
        "Auto",
        "English",
        "Português (Brasil)",
        "Español",
    ]
    assert next(entry for entry in entries if entry.key == "auto").checked is True
    assert next(entry for entry in entries if entry.key == "pt-BR").checked is False


def test_language_menu_entries_reflect_manual_selection() -> None:
    entries = build_language_menu_entries(
        LanguageSelection.explicit("es"),
        "en",
        Translator("en"),
    )

    assert next(entry for entry in entries if entry.key == "es").checked is True
    assert next(entry for entry in entries if entry.key == "auto").checked is False
