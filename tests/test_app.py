from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import ModuleType

import pytest

from trayffeine.app import _clear_logs, run_app
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
    def __init__(self, settings: StoredSettings | None = None) -> None:
        self._settings = settings or StoredSettings(
            language_selection=LanguageSelection.explicit("es"),
            restore_infinite=True,
        )

    def load(self) -> StoredSettings:
        return self._settings


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
    fake_windows.confirm_message_box = lambda title, message: True
    fake_windows.open_path_in_shell = lambda path: None

    monkeypatch.setattr(trayffeine.i18n, "detect_system_locale", lambda: "en")
    monkeypatch.setattr(
        trayffeine.app_logging,
        "configure_logging",
        lambda *args, **kwargs: Path("/tmp/trayffeine.log"),
    )
    monkeypatch.setattr(
        trayffeine.app_logging,
        "default_log_path",
        lambda: Path("/tmp/trayffeine.log"),
    )
    monkeypatch.setattr(
        trayffeine.settings,
        "SettingsStore",
        lambda: FakeSettingsStore(
            StoredSettings(
                language_selection=LanguageSelection.explicit("es"),
                restore_infinite=True,
                detailed_logging_enabled=True,
            )
        ),
    )
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
    assert tray.kwargs["detailed_logging_enabled"] is True
    assert tray.kwargs["detailed_logging_preference"] is True
    assert tray.kwargs["detailed_logging_locked"] is False
    assert callable(tray.kwargs["clear_logs"])
    assert callable(tray.kwargs["set_detailed_logging_enabled"])


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
    fake_windows.confirm_message_box = lambda title, message: True
    fake_windows.show_message_box = lambda title, message: dialog_calls.append((title, message))
    fake_windows.open_path_in_shell = lambda path: None

    monkeypatch.setattr(
        trayffeine.app_logging,
        "configure_logging",
        lambda *args, **kwargs: log_path,
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


def test_run_app_locks_detailed_logging_when_env_override_is_present(monkeypatch) -> None:
    import trayffeine.app_logging
    import trayffeine.i18n
    import trayffeine.service
    import trayffeine.settings
    import trayffeine.tray

    created: dict[str, object] = {}
    fake_windows = ModuleType("trayffeine.windows")
    fake_windows.SingleInstanceGuard = FakeGuard
    fake_windows.WindowsInputBackend = object
    fake_windows.confirm_message_box = lambda title, message: True
    fake_windows.open_path_in_shell = lambda path: None

    monkeypatch.setenv("TRAYFFEINE_LOG_LEVEL", "INFO")
    monkeypatch.setattr(trayffeine.i18n, "detect_system_locale", lambda: "en")
    monkeypatch.setattr(
        trayffeine.app_logging,
        "configure_logging",
        lambda *args, **kwargs: Path("/tmp/trayffeine.log"),
    )
    monkeypatch.setattr(
        trayffeine.app_logging,
        "default_log_path",
        lambda: Path("/tmp/trayffeine.log"),
    )
    monkeypatch.setattr(
        trayffeine.settings,
        "SettingsStore",
        lambda: FakeSettingsStore(
            StoredSettings(
                language_selection=LanguageSelection.auto(),
                restore_infinite=False,
                detailed_logging_enabled=False,
            )
        ),
    )
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

    tray = created["tray"]
    assert tray.kwargs["detailed_logging_enabled"] is True
    assert tray.kwargs["detailed_logging_preference"] is False
    assert tray.kwargs["detailed_logging_locked"] is True


def test_clear_logs_recreates_a_fresh_log_file(monkeypatch, tmp_path) -> None:
    import trayffeine.app_logging

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    log_path = tmp_path / "Trayffeine" / "logs" / "trayffeine.log"
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers = []

    try:
        trayffeine.app_logging.configure_logging(level=logging.INFO, log_path=log_path)
        logging.getLogger("trayffeine.tests").info("before clear")
        for handler in root.handlers:
            handler.flush()
        log_path.with_suffix(".log.1").write_text("backup", encoding="utf-8")

        _clear_logs(log_path)

        assert log_path.exists()
        assert not log_path.with_suffix(".log.1").exists()
        assert "Logs cleared from tray menu" in log_path.read_text(encoding="utf-8")
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers = previous_handlers
        root.setLevel(previous_level)


def test_clear_logs_restores_logging_even_when_file_cleanup_fails(monkeypatch, tmp_path) -> None:
    import trayffeine.app_logging

    log_path = tmp_path / "Trayffeine" / "logs" / "trayffeine.log"
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        trayffeine.app_logging,
        "clear_log_files",
        lambda path: calls.append(("clear", path))
        or (_ for _ in ()).throw(PermissionError("locked")),
    )
    monkeypatch.setattr(
        trayffeine.app_logging,
        "set_runtime_log_level",
        lambda level, *, log_path=None: calls.append(("restore", level, log_path)),
    )
    logging.getLogger().setLevel(logging.INFO)

    with pytest.raises(PermissionError):
        _clear_logs(log_path)

    assert calls == [
        ("clear", log_path),
        ("restore", logging.INFO, log_path),
    ]
