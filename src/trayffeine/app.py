from __future__ import annotations


def run_app() -> None:
    from .service import TrayffeineService
    from .tray import TrayIconController
    from .windows import SingleInstanceGuard, WindowsInputBackend

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
