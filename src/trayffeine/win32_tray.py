from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from pystray import Icon

pystray_win32 = None
if sys.platform == "win32":
    try:
        from pystray import _win32 as pystray_win32
    except Exception:  # pragma: no cover - only used on Windows with pystray win32 backend
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

            if lparam == pystray_win32.win32.WM_LBUTTONUP:
                return

            super()._on_notify(wparam, lparam)

else:

    class Win32DoubleClickIcon(Icon):
        def __init__(
            self,
            *args: Any,
            on_double_click: Callable[[], None] | None = None,  # noqa: ARG002
            **kwargs: Any,
        ) -> None:
            super().__init__(*args, **kwargs)


def create_icon(
    *,
    name: str,
    title: str,
    icon: object,
    menu: object,
    on_double_click: Callable[[], None] | None = None,
) -> Icon:
    if sys.platform == "win32" and pystray_win32 is not None:
        return Win32DoubleClickIcon(
            name=name,
            title=title,
            icon=icon,
            menu=menu,
            on_double_click=on_double_click,
        )
    return Icon(name=name, title=title, icon=icon, menu=menu)
