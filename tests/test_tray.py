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
        self.invocations = 0
        self.posted_callbacks: list[object] = []

    def run(self, setup: object = None) -> None:
        if setup is not None:
            setup(self)

    def invoke(self, callback) -> None:  # noqa: ANN001
        self.invocations += 1
        callback()

    def post(self, callback) -> None:  # noqa: ANN001
        self.posted_callbacks.append(callback)

    def update_menu(self) -> None:
        return

    def notify(self, message: str, title: str) -> None:
        self.notification = (title, message)

    def stop(self) -> None:
        return

    def run_posted(self) -> None:
        while self.posted_callbacks:
            callback = self.posted_callbacks.pop(0)
            callback()


def test_tray_controller_can_build_menu_with_grouped_entries(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    service = FakeService()
    controller = tray_module.TrayIconController(service, system_locale="en")

    menu_items = controller._icon.menu.items
    assert controller._icon.title == "Trayffeine: inactive"
    assert controller._effective_locale() == "en"
    assert [item.text for item in menu_items[:2]] == [
        f"Trayffeine v{__version__}",
        "Inactive",
    ]
    assert menu_items[3].text == "Infinite mode"
    assert menu_items[4].text == "Activate for"
    assert menu_items[5].text == "Stop"
    assert menu_items[7].text == "Preferences"
    assert menu_items[8].text == "Support"
    assert menu_items[10].text == "Quit"


def test_tray_controller_persists_language_infinite_and_logging_settings(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    service = FakeService()
    settings_store = FakeSettingsStore()
    controller = tray_module.TrayIconController(
        service,
        system_locale="en",
        initial_language_selection=LanguageSelection.explicit("es"),
        settings_store=settings_store,
        detailed_logging_enabled=True,
    )

    controller._toggle_infinite()

    assert settings_store.saved[-1] == StoredSettings(
        language_selection=LanguageSelection.explicit("es"),
        restore_infinite=True,
        detailed_logging_enabled=True,
    )


def test_tray_controller_clears_restore_flag_for_timed_mode(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    service = FakeService()
    settings_store = FakeSettingsStore()
    controller = tray_module.TrayIconController(
        service,
        system_locale="en",
        settings_store=settings_store,
    )

    service.activate(timedelta(minutes=15), "15m")

    assert settings_store.saved[-1].restore_infinite is False
    assert controller._icon.title == "Trayffeine: active for 0s | 15m 00s left"


def test_double_click_toggles_any_active_mode_back_to_inactive(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    service = FakeService()
    service.activate(timedelta(minutes=15), "15m")
    controller = tray_module.TrayIconController(service, system_locale="en")

    controller._toggle_infinite()

    assert service.mode.kind == "off"


def test_tray_controller_exposes_open_logs_action_in_support_menu(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    opened: list[str] = []
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        open_logs_folder=lambda: opened.append("logs"),
    )

    support_menu = _submenu(controller._icon.menu, "Support")
    logs_item = _menu_item(support_menu, "Open Logs Folder")
    logs_item.action(None, None)

    assert opened == ["logs"]


def test_tray_controller_exposes_clear_logs_action_with_confirmation(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    cleared: list[str] = []
    confirmations: list[tuple[str, str]] = []
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        clear_logs=lambda: cleared.append("cleared"),
        confirm_clear_logs=lambda title, body: confirmations.append((title, body)) or True,
    )

    support_menu = _submenu(controller._icon.menu, "Support")
    clear_logs_item = _menu_item(support_menu, "Clear Logs")
    clear_logs_item.action(None, None)
    controller._icon.run_posted()

    assert confirmations == [
        (
            "Clear Trayffeine logs?",
            "This will remove trayffeine.log and all rotated backups.\n\nContinue?",
        )
    ]
    assert cleared == ["cleared"]


def test_tray_controller_exposes_detailed_logging_toggle(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    toggled: list[bool] = []
    settings_store = FakeSettingsStore()
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        settings_store=settings_store,
        set_detailed_logging_enabled=lambda enabled: toggled.append(enabled),
        detailed_logging_enabled=False,
    )

    preferences_menu = _submenu(controller._icon.menu, "Preferences")
    detailed_item = _menu_item(preferences_menu, "Detailed logging")
    detailed_item.action(None, None)

    assert toggled == [True]
    assert controller._detailed_logging_enabled is True
    assert settings_store.saved[-1].detailed_logging_enabled is True
    refreshed_item = _menu_item(_submenu(controller._icon.menu, "Preferences"), "Detailed logging")
    assert _resolve_menu_flag(refreshed_item.checked, refreshed_item) is True


def test_tray_controller_disables_detailed_logging_toggle_when_locked(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    toggled: list[bool] = []
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        set_detailed_logging_enabled=lambda enabled: toggled.append(enabled),
        detailed_logging_enabled=True,
        detailed_logging_locked=True,
    )

    preferences_menu = _submenu(controller._icon.menu, "Preferences")
    detailed_item = _menu_item(preferences_menu, "Detailed logging")
    detailed_item.action(None, None)

    assert _resolve_menu_flag(detailed_item.checked, detailed_item) is True
    assert _resolve_menu_flag(detailed_item.enabled, detailed_item) is False
    assert toggled == []


def test_tray_controller_preserves_saved_logging_preference_when_env_lock_is_active(
    monkeypatch,
) -> None:
    tray_module = _load_tray_module(monkeypatch)

    service = FakeService()
    settings_store = FakeSettingsStore()
    controller = tray_module.TrayIconController(
        service,
        system_locale="en",
        settings_store=settings_store,
        detailed_logging_enabled=True,
        detailed_logging_preference=False,
        detailed_logging_locked=True,
    )

    controller._toggle_infinite()

    assert settings_store.saved[-1].detailed_logging_enabled is False


def test_tray_controller_does_not_clear_logs_when_confirmation_is_canceled(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    cleared: list[str] = []
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        clear_logs=lambda: cleared.append("cleared"),
        confirm_clear_logs=lambda title, body: False,  # noqa: ARG005
    )

    support_menu = _submenu(controller._icon.menu, "Support")
    clear_logs_item = _menu_item(support_menu, "Clear Logs")
    clear_logs_item.action(None, None)
    controller._icon.run_posted()

    assert cleared == []


def test_tray_controller_deduplicates_pending_clear_logs_dialogs(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    cleared: list[str] = []
    confirmations: list[tuple[str, str]] = []
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        clear_logs=lambda: cleared.append("cleared"),
        confirm_clear_logs=lambda title, body: confirmations.append((title, body)) or True,
    )

    support_menu = _submenu(controller._icon.menu, "Support")
    clear_logs_item = _menu_item(support_menu, "Clear Logs")
    clear_logs_item.action(None, None)
    clear_logs_item.action(None, None)
    controller._icon.run_posted()

    assert len(confirmations) == 1
    assert cleared == ["cleared"]


def _load_tray_module(monkeypatch):
    fake_pystray = ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem

    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    sys.modules.pop("trayffeine.win32_tray", None)
    sys.modules.pop("trayffeine.tray", None)
    return importlib.import_module("trayffeine.tray")


def _submenu(menu: FakeMenu, text: str) -> FakeMenu:
    return _menu_item(menu, text).action


def _menu_item(menu: FakeMenu, text: str) -> FakeMenuItem:
    return next(item for item in menu.items if getattr(item, "text", "") == text)


def _resolve_menu_flag(value: object, item: FakeMenuItem) -> bool:
    if callable(value):
        return bool(value(item))
    return bool(value)
