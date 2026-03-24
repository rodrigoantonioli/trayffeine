from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

from trayffeine.app import run_app
from trayffeine.i18n import LanguageSelection
from trayffeine.settings import StoredSettings


class FakeGuard:
    acquired = True

    @classmethod
    def acquire(cls, name: str):  # noqa: ARG003
        return cls()

    def release(self) -> None:
        return


class FakeSettingsStore:
    def load(self) -> StoredSettings:
        return StoredSettings(
            language_selection=LanguageSelection.explicit("es"),
            restore_infinite=True,
        )


class FakeService:
    def __init__(self, backend) -> None:  # noqa: ANN001
        self.backend = backend
        self.activations: list[tuple[object, str]] = []
        self.quit_called = False

    def activate(self, duration: object, preset_key: str) -> None:
        self.activations.append((duration, preset_key))

    def quit(self) -> None:
        self.quit_called = True


class FakeTray:
    def __init__(self, service, **kwargs) -> None:  # noqa: ANN001
        self.service = service
        self.kwargs = kwargs

    def run(self) -> None:
        return


class CrashingTray(FakeTray):
    def run(self) -> None:
        raise RuntimeError("boom")


def test_run_app_restores_only_infinite_mode(monkeypatch) -> None:
    import trayffeine.app_logging
    import trayffeine.i18n
    import trayffeine.service
    import trayffeine.settings
    import trayffeine.tray

    created: dict[str, object] = {}
    fake_windows = ModuleType("trayffeine.windows")
    fake_windows.SingleInstanceGuard = FakeGuard
    fake_windows.WindowsInputBackend = object
    fake_windows.open_path_in_shell = lambda path: None

    monkeypatch.setattr(trayffeine.i18n, "detect_system_locale", lambda: "en")
    monkeypatch.setattr(
        trayffeine.app_logging,
        "configure_logging",
        lambda: Path("/tmp/trayffeine.log"),
    )
    monkeypatch.setattr(
        trayffeine.app_logging,
        "default_log_path",
        lambda: Path("/tmp/trayffeine.log"),
    )
    monkeypatch.setattr(trayffeine.settings, "SettingsStore", lambda: FakeSettingsStore())
    monkeypatch.setitem(sys.modules, "trayffeine.windows", fake_windows)

    def create_service(*args, **kwargs):  # noqa: ANN002, ANN003
        service = FakeService(*args, **kwargs)
        created["service"] = service
        return service

    def create_tray(service, **kwargs):  # noqa: ANN001, ANN003
        tray = FakeTray(service, **kwargs)
        created["tray"] = tray
        return tray

    monkeypatch.setattr(trayffeine.service, "TrayffeineService", create_service)
    monkeypatch.setattr(trayffeine.tray, "TrayIconController", create_tray)

    run_app()

    service = created["service"]
    tray = created["tray"]

    assert service.activations == [(None, "infinite")]
    assert tray.kwargs["initial_language_selection"] == LanguageSelection.explicit("es")
    assert callable(tray.kwargs["open_logs_folder"])


def test_run_app_logs_and_shows_dialog_on_unhandled_exception(monkeypatch, tmp_path) -> None:
    import trayffeine.app_logging
    import trayffeine.i18n
    import trayffeine.service
    import trayffeine.settings
    import trayffeine.tray

    created: dict[str, object] = {}
    dialog_calls: list[tuple[str, str]] = []
    log_path = tmp_path / "logs" / "trayffeine.log"
    fake_windows = ModuleType("trayffeine.windows")
    fake_windows.SingleInstanceGuard = FakeGuard
    fake_windows.WindowsInputBackend = object
    fake_windows.show_message_box = lambda title, message: dialog_calls.append((title, message))
    fake_windows.open_path_in_shell = lambda path: None

    monkeypatch.setattr(
        trayffeine.app_logging,
        "configure_logging",
        lambda: log_path,
    )
    monkeypatch.setattr(
        trayffeine.app_logging,
        "default_log_path",
        lambda: log_path,
    )
    monkeypatch.setattr(trayffeine.i18n, "detect_system_locale", lambda: "en")
    monkeypatch.setattr(trayffeine.settings, "SettingsStore", lambda: FakeSettingsStore())
    monkeypatch.setitem(sys.modules, "trayffeine.windows", fake_windows)

    def create_service(*args, **kwargs):  # noqa: ANN002, ANN003
        service = FakeService(*args, **kwargs)
        created["service"] = service
        return service

    def create_tray(service, **kwargs):  # noqa: ANN001, ANN003
        tray = CrashingTray(service, **kwargs)
        created["tray"] = tray
        return tray

    monkeypatch.setattr(trayffeine.service, "TrayffeineService", create_service)
    monkeypatch.setattr(trayffeine.tray, "TrayIconController", create_tray)

    with pytest.raises(SystemExit) as exc_info:
        run_app()

    assert exc_info.value.code == 1
    assert created["service"].quit_called is True
    assert dialog_calls == [
        (
            "Trayffeine",
            f"Trayffeine hit an unexpected error.\n\nSee logs in:\n{log_path.parent}",
        )
    ]
    assert "RuntimeError: boom" in log_path.read_text(encoding="utf-8")
