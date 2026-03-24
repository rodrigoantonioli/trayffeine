from __future__ import annotations


def run_app() -> None:
    from .i18n import detect_system_locale
    from .service import TrayffeineService
    from .tray import TrayIconController
    from .windows import SingleInstanceGuard, WindowsInputBackend

    guard = SingleInstanceGuard.acquire("Local\\TrayffeineSingleInstance")
    if not guard.acquired:
        return

    service = TrayffeineService(backend=WindowsInputBackend())
    tray = TrayIconController(service, system_locale=detect_system_locale())
    try:
        tray.run()
    finally:
        service.quit()
        guard.release()
