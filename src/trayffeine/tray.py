from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw

from .assets import asset_path
from .i18n import LanguageSelection, LocaleCode, Translator, effective_locale
from .presenter import (
    build_duration_menu_entries,
    build_language_menu_entries,
    build_menu_entries,
    build_status_entries,
    icon_variant,
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
        settings_store: SettingsStore | None = None,
        open_logs_folder: Callable[[], None] | None = None,
    ) -> None:
        self._service = service
        self._system_locale = system_locale
        self._language_selection = initial_language_selection or LanguageSelection.auto()
        self._settings_store = settings_store
        self._open_logs_folder_callback = open_logs_folder
        self._service.set_callbacks(
            on_state_change=self._handle_state_change,
            on_timer_finished=self._notify_timer_finished,
            on_tick=self._request_refresh,
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
        LOGGER.info("Tray icon visible on thread=%s", threading.current_thread().name)

    def _build_menu(self) -> Menu:
        _, Menu, MenuItem = _pystray_types()
        snapshot = self._service.snapshot()
        translator = self._translator()
        status_entries = build_status_entries(snapshot.mode, snapshot.now, translator)
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
                MenuItem(translator.t("tray.menu.language"), self._build_language_menu()),
                MenuItem(
                    translator.t("tray.menu.open_logs"),
                    self._on_open_logs,
                    enabled=self._static_bool(self._open_logs_folder_callback is not None),
                ),
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

    def _make_activate_handler(self, preset_key: str):
        def handler(icon: Icon, item: MenuItem) -> None:  # noqa: ARG001
            preset = PRESET_BY_KEY[preset_key]
            self._service.activate(preset.duration, preset.key)

        return handler

    def _make_language_handler(self, selection_key: str):
        def handler(icon: Icon, item: MenuItem) -> None:  # noqa: ARG001
            if selection_key == "auto":
                self._language_selection = LanguageSelection.auto()
            else:
                self._language_selection = LanguageSelection.explicit(selection_key)
            self._persist_settings()
            self._request_refresh()

        return handler

    def _on_deactivate(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        self._service.deactivate()

    def _on_activate_infinite(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        self._service.activate(None, "infinite")

    def _on_open_logs(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        if self._open_logs_folder_callback is None:
            return
        try:
            self._open_logs_folder_callback()
        except Exception:
            LOGGER.exception("Failed to open Trayffeine logs folder")

    def _on_quit(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        self._service.quit()
        icon.stop()

    def _handle_state_change(self) -> None:
        self._persist_settings()
        self._request_refresh()

    def _request_refresh(self) -> None:
        LOGGER.info("Queueing tray refresh from thread=%s", threading.current_thread().name)
        invoke_icon_callback(self._icon, self._refresh)

    def _refresh(self) -> None:
        snapshot = self._service.snapshot()
        translator = self._translator()
        LOGGER.info(
            "Refreshing tray state kind=%s locale=%s thread=%s",
            snapshot.mode.kind,
            self._effective_locale(),
            threading.current_thread().name,
        )
        self._icon.icon = self._images[icon_variant(snapshot.mode, snapshot.now)]
        self._icon.title = tooltip_text(snapshot.mode, snapshot.now, translator)
        self._icon.menu = self._build_menu()
        if self._icon.visible:
            self._icon.update_menu()

    def _notify_timer_finished(self) -> None:
        self._persist_settings()
        invoke_icon_callback(self._icon, self._show_timer_finished_notification)

    def _show_timer_finished_notification(self) -> None:
        self._refresh()
        title, message = timer_finished_notification(self._translator())
        try:
            self._icon.notify(message, title)
        except NotImplementedError:
            return

    def _toggle_infinite(self) -> None:
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
        )
        self._settings_store.save(settings)

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
