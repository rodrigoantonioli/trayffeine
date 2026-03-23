from __future__ import annotations

from .service import TrayffeineService
from .tray import TrayIconController
from .windows import SingleInstanceGuard, WindowsInputBackend


def run_app() -> None:
    guard = SingleInstanceGuard.acquire("Local\\TrayffeineSingleInstance")
    if not guard.acquired:
        return

    service = TrayffeineService(backend=WindowsInputBackend())
    tray = TrayIconController(service)
    try:
        tray.run()
    finally:
        service.quit()
        guard.release()

