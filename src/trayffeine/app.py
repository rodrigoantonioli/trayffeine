from __future__ import annotations

import logging
import traceback
from dataclasses import replace
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def run_app() -> None:
    from .app_logging import (
        configure_logging,
        default_log_path,
        effective_log_level,
        is_detailed_logging_level,
        is_log_level_locked_by_env,
    )
    from .i18n import FALLBACK_LOCALE, Translator, detect_system_locale
    from .settings import SettingsStore

    log_path = default_log_path()
    settings_store = SettingsStore()
    settings = settings_store.load()
    startup_log_level = effective_log_level(settings.detailed_logging_enabled)
    try:
        log_path = configure_logging(level=startup_log_level, log_path=log_path)
        LOGGER.info("Trayffeine starting")
        _run_app(
            log_path,
            settings_store=settings_store,
            settings=settings,
            detailed_logging_enabled=is_detailed_logging_level(startup_log_level),
            detailed_logging_locked=is_log_level_locked_by_env(),
        )
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


def _run_app(
    log_path: Path,
    *,
    settings_store,
    settings,
    detailed_logging_enabled: bool,
    detailed_logging_locked: bool,
) -> None:  # noqa: ANN001
    from .i18n import detect_system_locale
    from .keepawake import effective_keepawake_method
    from .service import TrayffeineService
    from .tray import TrayIconController
    from .windows import (
        SingleInstanceGuard,
        confirm_message_box,
        copy_text_to_clipboard,
        create_keepawake_backend,
        is_start_with_windows_enabled,
        open_path_in_shell,
        set_start_with_windows_enabled,
        show_info_message_box,
    )

    guard = SingleInstanceGuard.acquire("Local\\TrayffeineSingleInstance")
    if not guard.acquired:
        return

    service = TrayffeineService(
        backend=create_keepawake_backend(
            effective_keepawake_method(
                settings.keepawake_method,
                presence_compatibility_enabled=settings.presence_compatibility_enabled,
            )
        )
    )
    start_with_windows_enabled = _sync_start_with_windows_setting(
        settings.start_with_windows,
        set_start_with_windows_enabled,
        is_start_with_windows_enabled,
    )
    if start_with_windows_enabled != settings.start_with_windows:
        settings = replace(settings, start_with_windows=start_with_windows_enabled)
        settings_store.save(settings)
    if settings.restore_infinite:
        service.activate(None, "infinite")
    tray = TrayIconController(
        service,
        system_locale=detect_system_locale(),
        initial_language_selection=settings.language_selection,
        initial_keepawake_method=settings.keepawake_method,
        initial_presence_compatibility_enabled=settings.presence_compatibility_enabled,
        initial_start_with_windows=start_with_windows_enabled,
        settings_store=settings_store,
        settings_path=settings_store.path,
        log_path=log_path,
        show_help=show_info_message_box,
        open_logs_folder=lambda: _open_logs_folder(log_path, open_path_in_shell),
        clear_logs=lambda: _clear_logs(log_path),
        copy_to_clipboard=copy_text_to_clipboard,
        confirm_clear_logs=confirm_message_box,
        set_detailed_logging_enabled=lambda enabled: _set_detailed_logging_enabled(
            log_path, enabled
        ),
        set_keepawake_method=lambda method: _set_keepawake_method(service, method),
        set_presence_compatibility_enabled=lambda enabled, method: (
            _set_presence_compatibility_enabled(service, method, enabled)
        ),
        set_start_with_windows_enabled=lambda enabled: _set_start_with_windows_from_tray(
            enabled, set_start_with_windows_enabled
        ),
        detailed_logging_enabled=detailed_logging_enabled,
        detailed_logging_preference=settings.detailed_logging_enabled,
        detailed_logging_locked=detailed_logging_locked,
    )
    try:
        tray.run()
    finally:
        LOGGER.info("Trayffeine exiting")
        service.quit()
        guard.release()


def _open_logs_folder(log_path: Path, open_path_in_shell) -> None:  # noqa: ANN001
    log_dir = log_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)
    open_path_in_shell(log_dir)


def _set_detailed_logging_enabled(log_path: Path, enabled: bool) -> None:
    from .app_logging import log_level_for_detailed_logging, set_runtime_log_level

    target_level = log_level_for_detailed_logging(enabled)
    if enabled:
        set_runtime_log_level(target_level, log_path=log_path)
        LOGGER.info("Detailed logging enabled from tray menu")
        return

    LOGGER.info("Detailed logging disabled from tray menu")
    set_runtime_log_level(target_level, log_path=log_path)


def _set_keepawake_method(
    service,
    method,
    presence_compatibility_enabled: bool = False,
) -> None:  # noqa: ANN001
    from .keepawake import effective_keepawake_method
    from .windows import create_keepawake_backend

    service.set_backend(
        create_keepawake_backend(
            effective_keepawake_method(
                method,
                presence_compatibility_enabled=presence_compatibility_enabled,
            )
        )
    )


def _set_presence_compatibility_enabled(service, method, enabled: bool) -> None:  # noqa: ANN001
    _set_keepawake_method(
        service,
        method,
        presence_compatibility_enabled=enabled,
    )


def _sync_start_with_windows_setting(
    enabled: bool,
    set_start_with_windows_enabled,
    is_start_with_windows_enabled,
) -> bool:  # noqa: ANN001
    try:
        applied_state = set_start_with_windows_enabled(enabled)
        if isinstance(applied_state, bool):
            return applied_state
    except Exception:
        LOGGER.exception("Failed to sync start-with-Windows setting at startup")
    try:
        return is_start_with_windows_enabled()
    except Exception:
        LOGGER.exception("Failed to read start-with-Windows state at startup")
        return enabled


def _set_start_with_windows_from_tray(
    enabled: bool,
    set_start_with_windows_enabled,
) -> None:  # noqa: ANN001
    applied_state = set_start_with_windows_enabled(enabled)
    if isinstance(applied_state, bool) and applied_state != enabled:
        raise RuntimeError("Windows did not apply the requested start-with-Windows state")


def _clear_logs(log_path: Path) -> None:
    from .app_logging import clear_log_files, set_runtime_log_level

    current_level = logging.getLogger().level
    try:
        clear_log_files(log_path)
    finally:
        set_runtime_log_level(current_level, log_path=log_path)
    LOGGER.info("Logs cleared from tray menu")


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
