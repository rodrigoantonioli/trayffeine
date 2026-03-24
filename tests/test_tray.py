from __future__ import annotations

from datetime import UTC, datetime

from trayffeine.service import ServiceSnapshot
from trayffeine.session import SessionMode
from trayffeine.tray import TrayIconController


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


def test_tray_controller_can_build_menu_with_localized_entries() -> None:
    controller = TrayIconController(FakeService(), system_locale="en")

    assert controller._icon.title == "Trayffeine"
    assert controller._effective_locale() == "en"
