from __future__ import annotations


def run_app() -> None:
    from .i18n import detect_system_locale
    from .service import TrayffeineService
    from .settings import SettingsStore
    from .tray import TrayIconController
    from .windows import SingleInstanceGuard, WindowsInputBackend

    guard = SingleInstanceGuard.acquire("Local\\TrayffeineSingleInstance")
    if not guard.acquired:
        return

    settings_store = SettingsStore()
    settings = settings_store.load()
    service = TrayffeineService(backend=WindowsInputBackend())
    if settings.restore_infinite:
        service.activate(None, "infinite")
    tray = TrayIconController(
        service,
        system_locale=detect_system_locale(),
        initial_language_selection=settings.language_selection,
        settings_store=settings_store,
    )
    try:
        tray.run()
    finally:
        service.quit()
        guard.release()
