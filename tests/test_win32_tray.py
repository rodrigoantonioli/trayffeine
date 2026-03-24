from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace


class FakeBaseIcon:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.notified: list[tuple[int, int]] = []

    def _on_notify(self, wparam: int, lparam: int) -> None:
        self.notified.append((wparam, lparam))


def test_win32_double_click_icon_toggles_without_forwarding_single_click(monkeypatch) -> None:
    fake_pystray = ModuleType("pystray")
    fake_pystray.__path__ = []
    fake_pystray.Icon = FakeBaseIcon
    fake_win32_module = ModuleType("pystray._win32")
    fake_win32_module.Icon = FakeBaseIcon
    fake_win32_module.win32 = SimpleNamespace(
        WM_LBUTTONDBLCLK=515,
        WM_LBUTTONUP=514,
        WM_RBUTTONUP=517,
    )

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    monkeypatch.setitem(sys.modules, "pystray._win32", fake_win32_module)
    sys.modules.pop("trayffeine.win32_tray", None)

    module = importlib.import_module("trayffeine.win32_tray")
    calls: list[str] = []
    icon = module.create_icon(
        name="trayffeine",
        title="Trayffeine",
        icon=object(),
        menu=object(),
        on_double_click=lambda: calls.append("double"),
    )

    icon._on_notify(0, fake_win32_module.win32.WM_LBUTTONUP)
    icon._on_notify(0, fake_win32_module.win32.WM_LBUTTONDBLCLK)
    icon._on_notify(0, fake_win32_module.win32.WM_RBUTTONUP)

    assert calls == ["double"]
    assert icon.notified == [(0, fake_win32_module.win32.WM_RBUTTONUP)]
