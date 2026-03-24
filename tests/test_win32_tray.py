from __future__ import annotations

import ctypes
import importlib
import sys
from types import ModuleType, SimpleNamespace

from trayffeine.win32_tray import CS_DBLCLKS, WM_TRAYFFEINE_INVOKE


class FakeBaseIcon:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.name = kwargs.get("name", "")
        self.notified: list[tuple[int, int]] = []
        self._message_handlers: dict[int, object] = {}
        self._running = False
        self._hwnd = None
        if hasattr(self, "_register_class"):
            self.atom = self._register_class()

    def _on_notify(self, wparam: int, lparam: int) -> None:
        self.notified.append((wparam, lparam))


class FakeWNDCLASSEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
        ("hIconSm", ctypes.c_void_p),
    ]


def test_win32_double_click_icon_toggles_and_preserves_base_notify_flow(monkeypatch) -> None:
    fake_pystray = ModuleType("pystray")
    fake_pystray.__path__ = []
    fake_pystray.Icon = FakeBaseIcon
    fake_win32_module = ModuleType("pystray._win32")
    fake_win32_module.Icon = FakeBaseIcon
    registered_styles: list[int] = []

    def register_class_ex(window_class) -> int:
        registered_styles.append(window_class.style)
        return 1

    fake_win32_module.win32 = SimpleNamespace(
        WM_LBUTTONDBLCLK=515,
        WM_LBUTTONUP=514,
        WM_RBUTTONUP=517,
        RegisterClassEx=register_class_ex,
        WNDCLASSEX=FakeWNDCLASSEX,
        GetModuleHandle=lambda _: 1,
        COLOR_WINDOW=5,
    )
    fake_win32_module._dispatcher = None

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
    assert registered_styles == [CS_DBLCLKS]
    assert icon.notified == [
        (0, fake_win32_module.win32.WM_LBUTTONUP),
        (0, fake_win32_module.win32.WM_RBUTTONUP),
    ]


def test_win32_icon_invoke_posts_back_to_icon_thread(monkeypatch) -> None:
    fake_pystray = ModuleType("pystray")
    fake_pystray.__path__ = []
    fake_pystray.Icon = FakeBaseIcon
    fake_win32_module = ModuleType("pystray._win32")
    fake_win32_module.Icon = FakeBaseIcon
    posted_messages: list[tuple[int, int, int, int]] = []

    fake_win32_module.win32 = SimpleNamespace(
        WM_LBUTTONDBLCLK=515,
        WM_LBUTTONUP=514,
        WM_RBUTTONUP=517,
        RegisterClassEx=lambda window_class: 1,
        WNDCLASSEX=FakeWNDCLASSEX,
        GetModuleHandle=lambda _: 1,
        COLOR_WINDOW=5,
        PostMessage=lambda hwnd, msg, wparam, lparam: posted_messages.append(
            (hwnd, msg, wparam, lparam)
        ),
    )
    fake_win32_module._dispatcher = None

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    monkeypatch.setitem(sys.modules, "pystray._win32", fake_win32_module)
    sys.modules.pop("trayffeine.win32_tray", None)

    module = importlib.import_module("trayffeine.win32_tray")
    icon = module.create_icon(
        name="trayffeine",
        title="Trayffeine",
        icon=object(),
        menu=object(),
    )
    calls: list[str] = []
    icon._running = True
    icon._hwnd = 99

    icon.invoke(lambda: calls.append("ran"))

    assert posted_messages == [(99, WM_TRAYFFEINE_INVOKE, 0, 0)]
    assert calls == []

    icon._on_invoke(0, 0)

    assert calls == ["ran"]
