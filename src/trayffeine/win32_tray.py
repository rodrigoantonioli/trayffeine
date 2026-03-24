from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from typing import Any

CS_DBLCLKS = 0x0008


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
                    super().__init__(*args, **kwargs)

                def _on_notify(self, wparam: int, lparam: int) -> None:
                    if lparam == pystray_win32.win32.WM_LBUTTONDBLCLK:
                        if self._on_double_click_callback is not None:
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

            return Win32DoubleClickIcon(
                name=name,
                title=title,
                icon=icon,
                menu=menu,
                on_double_click=on_double_click,
            )

    from pystray import Icon

    return Icon(name=name, title=title, icon=icon, menu=menu)
