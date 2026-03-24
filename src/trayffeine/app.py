from __future__ import annotations

import logging
import traceback
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def run_app() -> None:
    from .app_logging import configure_logging, default_log_path
    from .i18n import FALLBACK_LOCALE, Translator, detect_system_locale

    log_path = default_log_path()
    try:
        log_path = configure_logging()
        _run_app(log_path)
    except Exception as exc:
        _record_unhandled_exception(log_path)
        locale = FALLBACK_LOCALE
        try:
            locale = detect_system_locale()
        except Exception:
            LOGGER.exception("Failed to detect locale for crash dialog")

        try:
            from .windows import show_message_box

            translator = Translator(locale)
            show_message_box(
                translator.t("app.crash.title"),
                translator.t("app.crash.body", log_dir=str(log_path.parent)),
            )
        except Exception:
            LOGGER.exception("Failed to show crash dialog")
        raise SystemExit(1) from exc


def _run_app(log_path: Path) -> None:
    from .i18n import detect_system_locale
    from .service import TrayffeineService
    from .settings import SettingsStore
    from .tray import TrayIconController
    from .windows import SingleInstanceGuard, WindowsInputBackend, open_path_in_shell

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
        open_logs_folder=lambda: _open_logs_folder(log_path, open_path_in_shell),
    )
    try:
        tray.run()
    finally:
        service.quit()
        guard.release()


def _open_logs_folder(log_path: Path, open_path_in_shell) -> None:  # noqa: ANN001
    log_dir = log_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)
    open_path_in_shell(log_dir)


def _record_unhandled_exception(log_path: Path) -> None:
    LOGGER.exception("Unhandled exception in Trayffeine")
    if log_path.exists():
        return

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(traceback.format_exc())
    except OSError:
        return
