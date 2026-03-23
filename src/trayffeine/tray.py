from __future__ import annotations

from collections.abc import Callable

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from .assets import asset_path
from .presenter import build_menu_entries, icon_variant, tooltip_text
from .service import TrayffeineService
from .session import PRESETS


class TrayIconController:
    def __init__(self, service: TrayffeineService) -> None:
        self._service = service
        self._service.set_callbacks(
            on_state_change=self._refresh,
            on_timer_finished=self._notify_timer_finished,
        )
        self._images = {
            "active": self._load_image("trayffeine-active.png", fill="#9c5f2d"),
            "inactive": self._load_image("trayffeine-inactive.png", fill="#8b96a5"),
        }
        self._icon = Icon(
            name="trayffeine",
            title="Trayffeine",
            icon=self._images["inactive"],
            menu=self._build_menu(),
        )

    def run(self) -> None:
        self._icon.run(setup=self._setup)

    def _setup(self, icon: Icon) -> None:
        icon.visible = True
        self._refresh()

    def _build_menu(self) -> Menu:
        items = [
            MenuItem(
                preset.label,
                self._make_activate_handler(preset.key),
                checked=self._make_checked_handler(preset.key),
                radio=True,
            )
            for preset in PRESETS
        ]
        items.extend(
            [
                Menu.SEPARATOR,
                MenuItem("Desligar", self._on_deactivate, enabled=self._can_deactivate),
                MenuItem("Sair", self._on_quit),
            ]
        )
        return Menu(*items)

    def _make_activate_handler(self, preset_key: str) -> Callable[[Icon, MenuItem], None]:
        def handler(icon: Icon, item: MenuItem) -> None:  # noqa: ARG001
            preset = next(p for p in PRESETS if p.key == preset_key)
            self._service.activate(preset.duration, preset.key)

        return handler

    def _make_checked_handler(self, preset_key: str) -> Callable[[MenuItem], bool]:
        def checked(item: MenuItem) -> bool:  # noqa: ARG001
            snapshot = self._service.snapshot()
            entries = build_menu_entries(snapshot.mode, snapshot.now)
            entry = next(menu_entry for menu_entry in entries if menu_entry.key == preset_key)
            return entry.checked

        return checked

    def _can_deactivate(self, item: MenuItem) -> bool:  # noqa: ARG002
        snapshot = self._service.snapshot()
        entries = build_menu_entries(snapshot.mode, snapshot.now)
        return next(entry for entry in entries if entry.key == "off").enabled

    def _on_deactivate(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        self._service.deactivate()

    def _on_quit(self, icon: Icon, item: MenuItem) -> None:  # noqa: ARG002
        self._service.quit()
        icon.stop()

    def _refresh(self) -> None:
        snapshot = self._service.snapshot()
        self._icon.icon = self._images[icon_variant(snapshot.mode, snapshot.now)]
        self._icon.title = tooltip_text(snapshot.mode, snapshot.now)
        if self._icon.visible:
            self._icon.update_menu()

    def _notify_timer_finished(self) -> None:
        self._refresh()
        try:
            self._icon.notify(
                "Sessao encerrada. O Trayffeine voltou ao modo inativo.",
                "Trayffeine",
            )
        except NotImplementedError:
            return

    def _load_image(self, filename: str, *, fill: str) -> Image.Image:
        path = asset_path(filename)
        if path.exists():
            with Image.open(path) as image:
                return image.copy()
        return self._fallback_image(fill=fill)

    def _fallback_image(self, *, fill: str) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((16, 18, 48, 48), radius=8, fill=fill)
        draw.rectangle((22, 12, 42, 22), fill="#f3efe7")
        draw.arc((18, 20, 48, 46), start=270, end=90, fill="#f3efe7", width=4)
        return image

