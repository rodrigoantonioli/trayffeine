from __future__ import annotations

import json

from trayffeine.i18n import LanguageSelection
from trayffeine.settings import SettingsStore, StoredSettings, first_run_settings


def test_settings_store_round_trips_manual_locale_and_restore_flag(tmp_path) -> None:
    store = SettingsStore(tmp_path / "Trayffeine" / "settings.json")
    expected = StoredSettings(
        language_selection=LanguageSelection.explicit("pt-BR"),
        restore_infinite=True,
        detailed_logging_enabled=True,
        keepawake_method="shift",
        start_with_windows=True,
    )

    store.save(expected)

    assert store.load() == expected


def test_settings_store_defaults_to_auto_for_invalid_payload(tmp_path) -> None:
    settings_path = tmp_path / "Trayffeine" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"language_selection": {"mode": "manual", "locale": "fr"}}))

    loaded = SettingsStore(settings_path).load()

    assert loaded.language_selection == LanguageSelection.explicit("en")
    assert loaded.restore_infinite is False
    assert loaded.detailed_logging_enabled is False
    assert loaded.keepawake_method == "smart"
    assert loaded.start_with_windows is False


def test_settings_store_defaults_when_file_is_missing(tmp_path) -> None:
    loaded = SettingsStore(tmp_path / "Trayffeine" / "settings.json").load()

    assert loaded == first_run_settings()


def test_settings_store_defaults_keepawake_method_when_field_is_missing(tmp_path) -> None:
    settings_path = tmp_path / "Trayffeine" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps({"language_selection": {"mode": "manual", "locale": "pt-BR"}}),
        encoding="utf-8",
    )

    loaded = SettingsStore(settings_path).load()

    assert loaded.keepawake_method == "smart"
    assert loaded.start_with_windows is False
