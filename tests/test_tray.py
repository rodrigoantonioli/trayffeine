from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType

from trayffeine import __version__
from trayffeine.i18n import LanguageSelection
from trayffeine.service import ServiceSnapshot
from trayffeine.session import SessionMode
from trayffeine.settings import StoredSettings


class FakeService:
    def __init__(self) -> None:
        self.callbacks: dict[str, object] = {}
        self.mode = SessionMode.off()
        self.now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)

    def set_callbacks(self, **kwargs: object) -> None:
        self.callbacks = kwargs

    def snapshot(self) -> ServiceSnapshot:
        return ServiceSnapshot(mode=self.mode, now=self.now)

    def activate(self, duration: object, preset_key: str) -> None:  # noqa: ARG002
        if duration is None:
            self.mode = SessionMode.infinite(self.now)
        else:
            self.mode = SessionMode.timed(self.now, self.now + duration, preset_key)
        callback = self.callbacks.get("on_state_change")
        if callable(callback):
            callback()

    def deactivate(self) -> None:
        self.mode = SessionMode.off()
        callback = self.callbacks.get("on_state_change")
        if callable(callback):
            callback()

    def toggle_infinite(self) -> None:
        if self.mode.is_active(self.now):
            self.mode = SessionMode.off()
        else:
            self.mode = SessionMode.infinite(self.now)
        callback = self.callbacks.get("on_state_change")
        if callable(callback):
            callback()

    def quit(self) -> None:
        return


class FakeSettingsStore:
    def __init__(self) -> None:
        self.saved: list[StoredSettings] = []

    def save(self, settings: StoredSettings) -> None:
        self.saved.append(settings)


class FakeMenu:
    SEPARATOR = object()

    def __init__(self, *items: object) -> None:
        self.items = items


class FakeMenuItem:
    def __init__(
        self,
        text: str,
        action: object = None,
        *,
        checked: object = None,
        enabled: object = None,
        radio: bool = False,
    ) -> None:
        self.text = text
        self.action = action
        self.checked = checked
        self.enabled = enabled
        self.radio = radio


class FakeIcon:
    def __init__(self, *, name: str, title: str, icon: object, menu: object) -> None:
        self.name = name
        self.title = title
        self.icon = icon
        self.menu = menu
        self.visible = False

    def run(self, setup: object = None) -> None:
        if setup is not None:
            setup(self)

    def update_menu(self) -> None:
        return

    def notify(self, message: str, title: str) -> None:
        self.notification = (title, message)

    def stop(self) -> None:
        return


def test_tray_controller_can_build_menu_with_localized_entries(monkeypatch) -> None:
    fake_pystray = ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem

    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    sys.modules.pop("trayffeine.win32_tray", None)
    sys.modules.pop("trayffeine.tray", None)
    tray_module = importlib.import_module("trayffeine.tray")

    service = FakeService()
    controller = tray_module.TrayIconController(service, system_locale="en")

    assert controller._icon.title == "Trayffeine"
    assert controller._effective_locale() == "en"
    assert [item.text for item in controller._icon.menu.items[:3]] == [
        f"Trayffeine v{__version__}",
        "Elapsed: 0s",
        "Remaining: -",
    ]


def test_tray_controller_persists_language_and_infinite_mode(monkeypatch) -> None:
    fake_pystray = ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem

    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    sys.modules.pop("trayffeine.win32_tray", None)
    sys.modules.pop("trayffeine.tray", None)
    tray_module = importlib.import_module("trayffeine.tray")

    service = FakeService()
    settings_store = FakeSettingsStore()
    controller = tray_module.TrayIconController(
        service,
        system_locale="en",
        initial_language_selection=LanguageSelection.explicit("es"),
        settings_store=settings_store,
    )

    controller._toggle_infinite()

    assert settings_store.saved[-1].language_selection == LanguageSelection.explicit("es")
    assert settings_store.saved[-1].restore_infinite is True


def test_tray_controller_clears_restore_flag_for_timed_mode(monkeypatch) -> None:
    fake_pystray = ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem

    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    sys.modules.pop("trayffeine.win32_tray", None)
    sys.modules.pop("trayffeine.tray", None)
    tray_module = importlib.import_module("trayffeine.tray")

    service = FakeService()
    settings_store = FakeSettingsStore()
    controller = tray_module.TrayIconController(
        service,
        system_locale="en",
        settings_store=settings_store,
    )

    service.activate(timedelta(minutes=15), "15m")

    assert settings_store.saved[-1].restore_infinite is False
    assert controller._icon.title == "Trayffeine: active (15m 00s left)"


def test_double_click_toggles_any_active_mode_back_to_inactive(monkeypatch) -> None:
    fake_pystray = ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem

    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    sys.modules.pop("trayffeine.win32_tray", None)
    sys.modules.pop("trayffeine.tray", None)
    tray_module = importlib.import_module("trayffeine.tray")

    service = FakeService()
    service.activate(timedelta(minutes=15), "15m")
    controller = tray_module.TrayIconController(service, system_locale="en")

    controller._toggle_infinite()

    assert service.mode.kind == "off"
