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
        self.menu_updates = 0

    def run(self, setup: object = None) -> None:
        if setup is not None:
            setup(self)

    def invoke(self, callback) -> None:  # noqa: ANN001
        self.invocations += 1
        callback()

    def update_menu(self) -> None:
        self.menu_updates += 1

    def notify(self, message: str, title: str) -> None:
        self.notification = (title, message)

    def stop(self) -> None:
        return


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

    preferences_menu = _submenu(controller._icon.menu, "Preferences")
    assert _menu_item(preferences_menu, "Keep-awake method").text == "Keep-awake method"
    assert _menu_item(preferences_menu, "Language").text == "Language"

    support_menu = _submenu(controller._icon.menu, "Support")
    assert _menu_item(support_menu, "How it works").text == "How it works"
    assert _menu_item(support_menu, "Detailed logging").text == "Detailed logging"


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
        keepawake_method="smart",
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
    assert settings_store.saved[-1].keepawake_method == "smart"
    assert controller._icon.title == "Trayffeine: active for 0s | 15m 00s left"


def test_tray_tick_refresh_updates_only_tooltip(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    service = FakeService()
    controller = tray_module.TrayIconController(service, system_locale="en")
    controller._icon.visible = True

    service.activate(timedelta(minutes=15), "15m")
    controller._icon.menu_updates = 0
    service.now += timedelta(seconds=5)

    on_tick = service.callbacks.get("on_tick")
    assert callable(on_tick)
    on_tick()

    assert controller._icon.title == "Trayffeine: active for 5s | 14m 55s left"
    assert controller._icon.menu_updates == 0


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


def test_tray_controller_exposes_help_action_in_support_menu(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)
    _run_threads_inline(monkeypatch, tray_module)

    shown: list[tuple[str, str]] = []
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        show_help=lambda title, body: shown.append((title, body)),
    )

    support_menu = _submenu(controller._icon.menu, "Support")
    help_item = _menu_item(support_menu, "How it works")
    help_item.action(None, None)

    assert shown == [
        (
            "How Trayffeine works",
            "Trayffeine keeps your PC awake while a session is active.\n"
            "\n"
            "Infinite mode stays on until you stop it.\n"
            "Timed presets stop automatically when time runs out.\n"
            "Double-click the tray icon to toggle infinite mode.\n"
            "\n"
            "Methods:\n"
            "- Smart: tries Windows API, then F15, then Shift.\n"
            "- Windows API: uses the native Windows execution state API.\n"
            "- F15: simulates F15 periodically.\n"
            "- Shift: simulates Shift periodically.",
        )
    ]


def test_tray_controller_deduplicates_pending_help_dialogs(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    shown: list[tuple[str, str]] = []
    started_threads: list[object] = []

    class FakeThread:
        def __init__(self, *, target, name, daemon) -> None:  # noqa: ANN001
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            started_threads.append(self)

    monkeypatch.setattr(tray_module.threading, "Thread", FakeThread)
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        show_help=lambda title, body: shown.append((title, body)),
    )

    support_menu = _submenu(controller._icon.menu, "Support")
    help_item = _menu_item(support_menu, "How it works")
    help_item.action(None, None)
    help_item.action(None, None)
    assert len(started_threads) == 1
    started_threads[0].target()

    assert len(shown) == 1


def test_tray_controller_exposes_clear_logs_action_with_confirmation(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)
    _run_threads_inline(monkeypatch, tray_module)

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

    support_menu = _submenu(controller._icon.menu, "Support")
    detailed_item = _menu_item(support_menu, "Detailed logging")
    detailed_item.action(None, None)

    assert toggled == [True]
    assert controller._detailed_logging_enabled is True
    assert settings_store.saved[-1].detailed_logging_enabled is True
    refreshed_item = _menu_item(_submenu(controller._icon.menu, "Support"), "Detailed logging")
    assert _resolve_menu_flag(refreshed_item.checked, refreshed_item) is True


def test_tray_controller_exposes_keepawake_method_menu(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    selected: list[str] = []
    settings_store = FakeSettingsStore()
    controller = tray_module.TrayIconController(
        FakeService(),
        system_locale="en",
        settings_store=settings_store,
        initial_keepawake_method="execution-state",
        set_keepawake_method=lambda method: selected.append(method),
    )

    preferences_menu = _submenu(controller._icon.menu, "Preferences")
    keepawake_menu = _submenu(preferences_menu, "Keep-awake method")
    api_item = _menu_item(keepawake_menu, "Windows API")
    shift_item = _menu_item(keepawake_menu, "Shift")

    assert _resolve_menu_flag(api_item.checked, api_item) is True

    shift_item.action(None, None)

    assert selected == ["shift"]
    assert controller._keepawake_method == "shift"
    assert settings_store.saved[-1].keepawake_method == "shift"


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

    support_menu = _submenu(controller._icon.menu, "Support")
    detailed_item = _menu_item(support_menu, "Detailed logging")
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
    _run_threads_inline(monkeypatch, tray_module)

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

    assert cleared == []


def test_tray_controller_deduplicates_pending_clear_logs_dialogs(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    cleared: list[str] = []
    confirmations: list[tuple[str, str]] = []
    started_threads: list[object] = []

    class FakeThread:
        def __init__(self, *, target, name, daemon) -> None:  # noqa: ANN001
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            started_threads.append(self)

    monkeypatch.setattr(tray_module.threading, "Thread", FakeThread)
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
    assert len(started_threads) == 1
    started_threads[0].target()

    assert len(confirmations) == 1
    assert cleared == ["cleared"]


def test_tray_controller_timer_finished_refreshes_inactive_icon(monkeypatch) -> None:
    tray_module = _load_tray_module(monkeypatch)

    service = FakeService()
    service.activate(timedelta(minutes=15), "15m")
    controller = tray_module.TrayIconController(service, system_locale="en")

    service.mode = SessionMode.off()
    controller._notify_timer_finished()

    assert controller._icon.title == "Trayffeine: inactive"
    assert controller._icon.icon is controller._images["inactive"]
    assert controller._icon.notification == (
        "Trayffeine",
        "Session ended. Trayffeine returned to inactive mode.",
    )


def _load_tray_module(monkeypatch):
    fake_pystray = ModuleType("pystray")
    fake_pystray.Icon = FakeIcon
    fake_pystray.Menu = FakeMenu
    fake_pystray.MenuItem = FakeMenuItem

    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    sys.modules.pop("trayffeine.win32_tray", None)
    sys.modules.pop("trayffeine.tray", None)
    return importlib.import_module("trayffeine.tray")


def _run_threads_inline(monkeypatch, tray_module) -> None:  # noqa: ANN001
    class ImmediateThread:
        def __init__(self, *, target, name, daemon) -> None:  # noqa: ANN001
            self._target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            self._target()

    monkeypatch.setattr(tray_module.threading, "Thread", ImmediateThread)


def _submenu(menu: FakeMenu, text: str) -> FakeMenu:
    return _menu_item(menu, text).action


def _menu_item(menu: FakeMenu, text: str) -> FakeMenuItem:
    return next(item for item in menu.items if getattr(item, "text", "") == text)


def _resolve_menu_flag(value: object, item: FakeMenuItem) -> bool:
    if callable(value):
        return bool(value(item))
    return bool(value)
