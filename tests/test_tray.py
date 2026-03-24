from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime
from types import ModuleType

from trayffeine.service import ServiceSnapshot
from trayffeine.session import SessionMode


class FakeService:
    def __init__(self) -> None:
        self.callbacks: dict[str, object] = {}

    def set_callbacks(self, **kwargs: object) -> None:
        self.callbacks = kwargs

    def snapshot(self) -> ServiceSnapshot:
        return ServiceSnapshot(
            mode=SessionMode.off(),
            now=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
        )

    def activate(self, duration: object, preset_key: str) -> None:  # noqa: ARG002
        return

    def deactivate(self) -> None:
        return

    def quit(self) -> None:
        return


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
    sys.modules.pop("trayffeine.tray", None)
    tray_module = importlib.import_module("trayffeine.tray")

    controller = tray_module.TrayIconController(FakeService(), system_locale="en")

    assert controller._icon.title == "Trayffeine"
    assert controller._effective_locale() == "en"
