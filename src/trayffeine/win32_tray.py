from __future__ import annotations

import ctypes
import logging
import queue
import sys
import threading
from collections.abc import Callable
from typing import Any

CS_DBLCLKS = 0x0008
WM_LBUTTONDBLCLK = 0x0203
WM_TRAYFFEINE_INVOKE = 0x0400 + 42

LOGGER = logging.getLogger(__name__)


def create_icon(
    *,
    name: str,
    title: str,
    icon: object,
    menu: object,
    on_double_click: Callable[[], None] | None = None,
) -> object:
    if sys.platform == "win32":
        try:
            from pystray import _win32 as pystray_win32
        except Exception:
            pystray_win32 = None

        if pystray_win32 is not None:

            class Win32DoubleClickIcon(pystray_win32.Icon):  # type: ignore[misc]
                def __init__(
                    self,
                    *args: Any,
                    on_double_click: Callable[[], None] | None = None,
                    **kwargs: Any,
                ) -> None:
                    self._on_double_click_callback = on_double_click
                    self._invoke_queue: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
                    super().__init__(*args, **kwargs)
                    self._message_handlers[WM_TRAYFFEINE_INVOKE] = self._on_invoke

                def _on_notify(self, wparam: int, lparam: int) -> None:
                    LOGGER.info(
                        "Tray notify lparam=%s thread=%s",
                        lparam,
                        threading.current_thread().name,
                    )
                    if lparam == WM_LBUTTONDBLCLK:
                        if self._on_double_click_callback is not None:
                            LOGGER.info("Handling tray double click")
                            self._on_double_click_callback()
                        return

                    super()._on_notify(wparam, lparam)

                def _register_class(self) -> int:
                    return pystray_win32.win32.RegisterClassEx(pystray_win32.win32.WNDCLASSEX(
                        cbSize=ctypes.sizeof(pystray_win32.win32.WNDCLASSEX),
                        style=CS_DBLCLKS,
                        lpfnWndProc=pystray_win32._dispatcher,
                        cbClsExtra=0,
                        cbWndExtra=0,
                        hInstance=pystray_win32.win32.GetModuleHandle(None),
                        hIcon=None,
                        hCursor=None,
                        hbrBackground=pystray_win32.win32.COLOR_WINDOW + 1,
                        lpszMenuName=None,
                        lpszClassName=f"{self.name}{id(self)}SystemTrayIcon",
                        hIconSm=None,
                    ))

                def invoke(self, callback: Callable[[], None]) -> None:
                    if (
                        not getattr(self, "_running", False)
                        or getattr(self, "_hwnd", None) is None
                        or threading.current_thread() is getattr(self, "_thread", None)
                    ):
                        LOGGER.info(
                            "Running tray callback inline thread=%s",
                            threading.current_thread().name,
                        )
                        callback()
                        return

                    self._invoke_queue.put(callback)
                    LOGGER.info("Posting tray callback to icon thread")
                    pystray_win32.win32.PostMessage(
                        self._hwnd,
                        WM_TRAYFFEINE_INVOKE,
                        0,
                        0,
                    )

                def _on_invoke(self, wparam: int, lparam: int) -> None:  # noqa: ARG002
                    LOGGER.info("Processing posted tray callbacks")
                    while True:
                        try:
                            callback = self._invoke_queue.get_nowait()
                        except queue.Empty:
                            return
                        callback()

            return Win32DoubleClickIcon(
                name=name,
                title=title,
                icon=icon,
                menu=menu,
                on_double_click=on_double_click,
            )

    from pystray import Icon

    return Icon(name=name, title=title, icon=icon, menu=menu)


def invoke_icon_callback(icon: object, callback: Callable[[], None]) -> None:
    invoke = getattr(icon, "invoke", None)
    if callable(invoke):
        invoke(callback)
        return
    callback()
