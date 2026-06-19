from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw

from . import __version__
from .assets import asset_path
from .diagnostics import DiagnosticsInfo, build_diagnostics_text
from .i18n import LanguageSelection, LocaleCode, Translator, effective_locale
from .keepawake import DEFAULT_KEEPAWAKE_METHOD, KeepAwakeMethod
from .presenter import (
    build_duration_menu_entries,
    build_keepawake_method_menu_entries,
    build_language_menu_entries,
    build_menu_entries,
    build_status_entries,
    icon_variant,
    menu_summary_text,
    timer_finished_notification,
    tooltip_text,
)
from .service import TrayffeineService
from .session import PRESET_BY_KEY
from .settings import SettingsStore, StoredSettings
from .win32_tray import create_icon, invoke_icon_callback

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pystray import Icon, Menu, MenuItem


def _pystray_types() -> tuple[Any, Any, Any]:
    from pystray import Icon, Menu, MenuItem

    return Icon, Menu, MenuItem


class TrayIconController:
    def __init__(
        self,
        service: TrayffeineService,
        *,
        system_locale: LocaleCode,
        initial_language_selection: LanguageSelection | None = None,
        initial_keepawake_method: KeepAwakeMethod = DEFAULT_KEEPAWAKE_METHOD,
        initial_presence_compatibility_enabled: bool = False,
        initial_start_with_windows: bool = False,
        settings_store: SettingsStore | None = None,
        settings_path: Path | None = None,
        log_path: Path | None = None,
        show_help: Callable[[str, str], None] | None = None,
        open_logs_folder: Callable[[], None] | None = None,
        clear_logs: Callable[[], None] | None = None,
        copy_to_clipboard: Callable[[str], None] | None = None,
        confirm_clear_logs: Callable[[str, str], bool] | None = None,
        set_detailed_logging_enabled: Callable[[bool], None] | None = None,
        set_keepawake_method: Callable[[KeepAwakeMethod], None] | None = None,
        set_presence_compatibility_enabled: Callable[[bool, KeepAwakeMethod], None]
        | None = None,
        set_start_with_windows_enabled: Callable[[bool], None] | None = None,
        detailed_logging_enabled: bool = False,
        detailed_logging_preference: bool | None = None,
        detailed_logging_locked: bool = False,
    ) -> None:
        self._service = service
        self._system_locale = system_locale
        self._language_selection = initial_language_selection or LanguageSelection.auto()
        self._keepawake_method = initial_keepawake_method
        self._presence_compatibility_enabled = initial_presence_compatibility_enabled
        self._settings_store = settings_store
        self._settings_path = settings_path
        self._log_path = log_path
        self._show_help_callback = show_help
        self._open_logs_folder_callback = open_logs_folder
        self._clear_logs_callback = clear_logs
        self._copy_to_clipboard_callback = copy_to_clipboard
        self._confirm_clear_logs_callback = confirm_clear_logs
        self._set_detailed_logging_enabled_callback = set_detailed_logging_enabled
        self._set_keepawake_method_callback = set_keepawake_method
        self._set_presence_compatibility_enabled_callback = (
            set_presence_compatibility_enabled
        )
        self._set_start_with_windows_enabled_callback = set_start_with_windows_enabled
        self._detailed_logging_enabled = detailed_logging_enabled
        self._detailed_logging_preference = (
            detailed_logging_enabled
            if detailed_logging_preference is None
            else detailed_logging_preference
        )
        self._detailed_logging_locked = detailed_logging_locked
        self._start_with_windows_enabled = initial_start_with_windows
        self._help_flow_pending = False
        self._clear_logs_flow_pending = False
        self._service.set_callbacks(
            on_state_change=self._handle_state_change,
            on_timer_finished=self._notify_timer_finished,
            on_tick=self._request_tooltip_refresh,
        )
        self._images = {
            "active": self._load_image("trayffeine-active.png", fill="#9c5f2d"),
            "inactive": self._load_image("trayffeine-inactive.png", fill="#8b96a5"),
        }
        snapshot = self._service.snapshot()
        translator = self._translator()
        self._icon = create_icon(
            name="trayffeine",
            title=tooltip_text(snapshot.mode, snapshot.now, translator),
            icon=self._images[icon_variant(snapshot.mode, snapshot.now)],
            menu=self._build_menu(),
            on_double_click=self._toggle_infinite,
        )

    def run(self) -> None:
        self._icon.run(setup=self._setup)

    def _setup(self, icon: Icon) -> None:
        icon.visible = True

    def _build_menu(self) -> Menu:
        _, Menu, MenuItem = _pystray_types()
        snapshot = self._service.snapshot()
        translator = self._translator()
        status_entries = build_status_entries(
            snapshot.mode,
            snapshot.now,
            translator,
            configured_method=self._keepawake_method,
            effective_method=snapshot.effective_keepawake_method,
            presence_compatibility_enabled=self._presence_compatibility_enabled,
        )
        entries = build_menu_entries(snapshot.mode, snapshot.now, translator)
        duration_entries = build_duration_menu_entries(snapshot.mode, snapshot.now, translator)
        infinite_entry = next(entry for entry in entries if entry.key == "infinite")
        stop_entry = next(entry for entry in entries if entry.key == "stop")
        quit_entry = next(entry for entry in entries if entry.key == "quit")

        items = [
            MenuItem(entry.text, self._noop, enabled=self._static_bool(False))
            for entry in status_entries
        ]
        items.append(Menu.SEPARATOR)

        items.extend(
            [
                MenuItem(
                    infinite_entry.text,
                    self._on_activate_infinite,
                    checked=self._static_bool(infinite_entry.checked),
                    enabled=self._static_bool(infinite_entry.enabled),
                ),
                MenuItem(
                    translator.t("tray.menu.activate_for"),
                    self._build_duration_menu(duration_entries),
                ),
                MenuItem(
                    stop_entry.text,
                    self._on_deactivate,
                    enabled=self._static_bool(stop_entry.enabled),
                ),
                Menu.SEPARATOR,
                MenuItem(
                    translator.t("tray.menu.preferences"),
                    self._build_preferences_menu(),
                ),
                MenuItem(translator.t("tray.menu.support"), self._build_support_menu()),
                Menu.SEPARATOR,
                MenuItem(quit_entry.text, self._on_quit),
            ]
        )
        return Menu(*items)

    def _build_duration_menu(self, entries: tuple[Any, ...]) -> Menu:
        _, Menu, MenuItem = _pystray_types()
        return Menu(
            *[
                MenuItem(
                    entry.text,
                    self._make_activate_handler(entry.key),
                    checked=self._static_bool(entry.checked),
                    radio=True,
                )
                for entry in entries
            ]
        )

    def _build_language_menu(self) -> Menu:
        _, Menu, MenuItem = _pystray_types()
        translator = self._translator()
        entries = build_language_menu_entries(
            self._language_selection,
            self._system_locale,
            translator,
        )
        return Menu(
            *[
                MenuItem(
                    entry.text,
                    self._make_language_handler(entry.key),
                    checked=self._static_bool(entry.checked),
                    radio=True,
                )
                for entry in entries
            ]
        )

    def _build_keepawake_method_menu(self) -> Menu:
        _, Menu, MenuItem = _pystray_types()
        translator = self._translator()
        entries = build_keepawake_method_menu_entries(self._keepawake_method, translator)
        return Menu(
            *[
                MenuItem(
                    entry.text,
                    self._make_keepawake_method_handler(entry.key),
                    checked=self._static_bool(entry.checked),
                    radio=True,
                )
                for entry in entries
            ]
        )

    def _build_preferences_menu(self) -> Menu:
        _, Menu, MenuItem = _pystray_types()
        translator = self._translator()
        return Menu(
            MenuItem(
                translator.t("tray.menu.presence_compatibility"),
                self._on_toggle_presence_compatibility,
                checked=self._static_bool(self._presence_compatibility_enabled),
                enabled=self._static_bool(
                    self._set_presence_compatibility_enabled_callback is not None
                ),
            ),
            MenuItem(
                translator.t("tray.menu.keepawake_method"),
                self._build_keepawake_method_menu(),
            ),
            MenuItem(
                translator.t("tray.menu.start_with_windows"),
                self._on_toggle_start_with_windows,
                checked=self._static_bool(self._start_with_windows_enabled),
                enabled=self._static_bool(
                    self._set_start_with_windows_enabled_callback is not None
                ),
            ),
            MenuItem(translator.t("tray.menu.language"), self._build_language_menu()),
        )

    def _build_support_menu(self) -> Menu:
        _, Menu, MenuItem = _pystray_types()
        translator = self._translator()
        return Menu(
            MenuItem(
                translator.t("tray.menu.copy_diagnostics"),
                self._on_copy_diagnostics,
                enabled=self._static_bool(self._copy_to_clipboard_callback is not None),
            ),
            Menu.SEPARATOR,
            MenuItem(
                translator.t("tray.menu.help"),
                self._on_show_help,
                enabled=self._static_bool(self._show_help_callback is not None),
            ),
            Menu.SEPARATOR,
            MenuItem(
                translator.t("tray.menu.detailed_logging"),
                self._on_toggle_detailed_logging,
                checked=self._static_bool(self._detailed_logging_enabled),
                enabled=self._static_bool(
                    self._set_detailed_logging_enabled_callback is not None
                    and not self._detailed_logging_locked
                ),
            ),
            MenuItem(
                translator.t("tray.menu.open_logs"),
                self._on_open_logs,
                enabled=self._static_bool(self._open_logs_folder_callback is not None),
            ),
            MenuItem(
                translator.t("tray.menu.clear_logs"),
                self._on_clear_logs,
                enabled=self._static_bool(self._clear_logs_callback is not None),
            ),
        )

    def _make_activate_handler(self, preset_key: str):
        def handler(icon: Icon, item: MenuItem) -> None:  # noqa: ARG001
            preset = PRESET_BY_KEY[preset_key]
            LOGGER.info("Timed preset selected from tray menu: %s", preset.key)
            self._service.activate(preset.duration, preset.key)

        return handler

    def _make_keepawake_method_handler(self, method: KeepAwakeMethod):
        def handler(icon: Icon, item: MenuItem) -> None:  # noqa: ARG001
            if (
                self._set_keepawake_method_callback is not None
                and not self._presence_compatibility_enabled
            ):
                try:
                    self._set_keepawake_method_callback(method)
                except Exception:
                    LOGGER.exception("Failed to change keep-awake method")
                    return

            self._keepawake_method = method
            self._persist_settings()
            LOGGER.info("Keep-awake method changed from tray menu: %s", method)
            self._request_refresh()

        return handler

    def _make_language_handler(self, selection_key: str):
        def handler(icon: Icon, item: MenuItem) -> None:  # noqa: ARG001
            if selection_key == "auto":
                self._language_selection = LanguageSelection.auto()
            else:
                self._language_selection = LanguageSelection.explicit(selection_key)
            self._persist_settings()
            LOGGER.info("Language selection changed from tray menu: %s", selection_key)
            self._request_refresh()

        return handler

    def _on_deactivate(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        LOGGER.info("Session stopped from tray menu")
        self._service.deactivate()

    def _on_activate_infinite(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        LOGGER.info("Infinite mode enabled from tray menu")
        self._service.activate(None, "infinite")

    def _on_open_logs(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        if self._open_logs_folder_callback is None:
            return
        try:
            LOGGER.info("Opening logs folder from tray menu")
            self._open_logs_folder_callback()
        except Exception:
            LOGGER.exception("Failed to open Trayffeine logs folder")

    def _on_show_help(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        if self._show_help_callback is None or self._help_flow_pending:
            return

        self._help_flow_pending = True
        self._start_help_flow()

    def _on_clear_logs(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        if self._clear_logs_callback is None or self._clear_logs_flow_pending:
            return

        self._clear_logs_flow_pending = True
        self._start_clear_logs_flow()

    def _on_toggle_detailed_logging(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        if self._detailed_logging_locked:
            return

        enabled = not self._detailed_logging_enabled
        if self._set_detailed_logging_enabled_callback is not None:
            try:
                self._set_detailed_logging_enabled_callback(enabled)
            except Exception:
                LOGGER.exception("Failed to change detailed logging state")
                return

        self._detailed_logging_enabled = enabled
        self._detailed_logging_preference = enabled
        self._persist_settings()
        self._request_refresh()

    def _on_toggle_presence_compatibility(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        enabled = not self._presence_compatibility_enabled
        if self._set_presence_compatibility_enabled_callback is not None:
            try:
                self._set_presence_compatibility_enabled_callback(
                    enabled,
                    self._keepawake_method,
                )
            except Exception:
                LOGGER.exception("Failed to change presence compatibility state")
                return

        self._presence_compatibility_enabled = enabled
        LOGGER.info("Presence compatibility changed from tray menu: %s", enabled)
        self._persist_settings()
        self._request_refresh()

    def _on_copy_diagnostics(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        if self._copy_to_clipboard_callback is None:
            return

        try:
            diagnostics = build_diagnostics_text(self._diagnostics_info())
            self._copy_to_clipboard_callback(diagnostics)
            LOGGER.info("Diagnostics copied from tray menu")
            title = self._translator().t("tray.notify.diagnostics_copied.title")
            message = self._translator().t("tray.notify.diagnostics_copied.body")
            self._icon.notify(message, title)
        except NotImplementedError:
            return
        except Exception:
            LOGGER.exception("Failed to copy Trayffeine diagnostics")

    def _on_toggle_start_with_windows(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        enabled = not self._start_with_windows_enabled
        if self._set_start_with_windows_enabled_callback is not None:
            try:
                self._set_start_with_windows_enabled_callback(enabled)
            except Exception:
                LOGGER.exception("Failed to update start-with-Windows setting")
                return

        self._start_with_windows_enabled = enabled
        LOGGER.info("Start with Windows changed from tray menu: %s", enabled)
        self._persist_settings()
        self._request_refresh()

    def _on_quit(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        self._service.quit()
        icon.stop()

    def _handle_state_change(self) -> None:
        self._persist_settings()
        self._request_refresh()

    def _request_refresh(self) -> None:
        invoke_icon_callback(self._icon, self._refresh)

    def _request_tooltip_refresh(self) -> None:
        invoke_icon_callback(self._icon, self._refresh_tooltip)

    def _refresh(self) -> None:
        snapshot = self._service.snapshot()
        translator = self._translator()
        self._icon.icon = self._images[icon_variant(snapshot.mode, snapshot.now)]
        self._icon.title = tooltip_text(snapshot.mode, snapshot.now, translator)
        self._icon.menu = self._build_menu()
        if self._icon.visible:
            self._icon.update_menu()

    def _refresh_tooltip(self) -> None:
        snapshot = self._service.snapshot()
        self._icon.title = tooltip_text(snapshot.mode, snapshot.now, self._translator())

    def _notify_timer_finished(self) -> None:
        self._persist_settings()
        LOGGER.info("Timed session finished and Trayffeine returned to inactive mode")
        invoke_icon_callback(self._icon, self._show_timer_finished_notification)

    def _show_timer_finished_notification(self) -> None:
        self._refresh()
        title, message = timer_finished_notification(self._translator())
        try:
            self._icon.notify(message, title)
        except NotImplementedError:
            return

    def _run_clear_logs_flow(self) -> None:
        try:
            translator = self._translator()
            if self._confirm_clear_logs_callback is not None:
                confirmed = self._confirm_clear_logs_callback(
                    translator.t("tray.logs.clear.title"),
                    translator.t("tray.logs.clear.body"),
                )
                if not confirmed:
                    return

            if self._clear_logs_callback is None:
                return

            self._clear_logs_callback()
        except Exception:
            LOGGER.exception("Failed to clear Trayffeine logs")
        finally:
            self._clear_logs_flow_pending = False

    def _run_help_flow(self) -> None:
        try:
            if self._show_help_callback is None:
                return

            translator = self._translator()
            LOGGER.info("Opening help dialog from tray menu")
            self._show_help_callback(
                translator.t("tray.help.title"),
                translator.t("tray.help.body"),
            )
        except Exception:
            LOGGER.exception("Failed to show Trayffeine help dialog")
        finally:
            self._help_flow_pending = False

    def _start_clear_logs_flow(self) -> None:
        threading.Thread(
            target=self._run_clear_logs_flow,
            name="trayffeine-clear-logs",
            daemon=True,
        ).start()

    def _start_help_flow(self) -> None:
        threading.Thread(
            target=self._run_help_flow,
            name="trayffeine-help",
            daemon=True,
        ).start()

    def _toggle_infinite(self) -> None:
        snapshot = self._service.snapshot()
        if snapshot.mode.is_active(snapshot.now):
            LOGGER.info("Double-click disabled the active Trayffeine session")
        else:
            LOGGER.info("Double-click enabled infinite mode")
        self._service.toggle_infinite()

    def _translator(self) -> Translator:
        return Translator(self._effective_locale())

    def _effective_locale(self) -> LocaleCode:
        return effective_locale(self._language_selection, self._system_locale)

    def _static_bool(self, value: bool) -> Callable[[MenuItem], bool]:
        def inner(item: MenuItem) -> bool:  # noqa: ARG001
            return value

        return inner

    def _noop(self, icon: Icon | None = None, item: MenuItem | None = None) -> None:  # noqa: ARG002
        return

    def _persist_settings(self) -> None:
        if self._settings_store is None:
            return

        snapshot = self._service.snapshot()
        settings = StoredSettings(
            language_selection=self._language_selection,
            restore_infinite=(
                snapshot.mode.kind == "infinite"
                and snapshot.mode.is_active(snapshot.now)
            ),
            detailed_logging_enabled=self._detailed_logging_preference,
            keepawake_method=self._keepawake_method,
            start_with_windows=self._start_with_windows_enabled,
            presence_compatibility_enabled=self._presence_compatibility_enabled,
        )
        self._settings_store.save(settings)

    def _diagnostics_info(self) -> DiagnosticsInfo:
        snapshot = self._service.snapshot()
        return DiagnosticsInfo(
            version=__version__,
            language_selection=self._language_selection_text(),
            effective_locale=self._effective_locale(),
            session_state=menu_summary_text(snapshot.mode, snapshot.now, Translator("en")),
            configured_keepawake_method=self._keepawake_method,
            effective_keepawake_method=snapshot.effective_keepawake_method,
            presence_compatibility_enabled=self._presence_compatibility_enabled,
            detailed_logging_enabled=self._detailed_logging_enabled,
            start_with_windows=self._start_with_windows_enabled,
            settings_path=str(self._settings_path) if self._settings_path else "-",
            log_path=str(self._log_path) if self._log_path else "-",
        )

    def _language_selection_text(self) -> str:
        if self._language_selection.mode == "manual":
            return f"manual:{self._language_selection.locale}"
        return "auto"

    def _load_image(self, filename: str, *, fill: str) -> Image.Image:
        path = asset_path(filename)
        if path.exists():
            with Image.open(path) as image:
                return image.copy()
        return self._fallback_image(fill=fill)

    def _fallback_image(self, *, fill: str) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 44, 52, 56), fill=(0, 0, 0, 32))
        draw.rounded_rectangle((16, 20, 48, 48), radius=8, fill=fill)
        draw.rounded_rectangle((16, 16, 48, 26), radius=6, fill="#f3efe7")
        draw.arc((20, 24, 48, 46), start=270, end=90, fill="#f3efe7", width=4)
        return image
